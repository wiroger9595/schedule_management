import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:async';
import 'dart:convert';
import '../models/schedule.dart';
import '../services/api_service.dart';
import 'add_schedule_screen.dart';
import '../utils/constants.dart'; // Added for ScheduleStatus

class MapScreen extends StatefulWidget {
  final Schedule schedule;

  MapScreen({required this.schedule});

  @override
  _MapScreenState createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  Completer<GoogleMapController> _controller = Completer();
  Position? _currentPosition;
  int? _estimatedTravelTimeMinutes; // In minutes
  bool _isLate = false;
  Map<String, dynamic> _allEstimates = {};
  String _selectedMode = 'car';
  late Schedule _schedule;
  int _selectedAttendeeIndex = 0;

  @override
  void initState() {
    super.initState();
    _schedule = widget.schedule;
    _selectedMode = _schedule.transportMode ?? 'car';
    _checkLocationAndTravel();
  }

  Future<void> _checkLocationAndTravel() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return;

    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }

    Position position = await Geolocator.getCurrentPosition();
    if (!mounted) return;

    setState(() {
      _currentPosition = position;
    });

    // If coords are missing but location name exists, geocode on-the-fly
    if ((_schedule.latitude == null || _schedule.longitude == null) &&
        _schedule.location != null && _schedule.location!.isNotEmpty) {
      print('No destination coordinates, geocoding from location name: ${_schedule.location}');
      try {
        final apiService = ApiService();
        final places = await apiService.searchPlaces(_schedule.location!, null, null);
        if (places.isNotEmpty && mounted) {
          final lat = (places.first['lat'] as num?)?.toDouble();
          final lon = (places.first['lon'] as num?)?.toDouble();
          if (lat != null && lon != null) {
            setState(() {
              _schedule = Schedule(
                id: _schedule.id,
                title: _schedule.title,
                description: _schedule.description,
                startTime: _schedule.startTime,
                endTime: _schedule.endTime,
                location: _schedule.location,
                transportMode: _schedule.transportMode,
                status: _schedule.status,
                latitude: lat,
                longitude: lon,
                isOnline: _schedule.isOnline,
                attendIds: _schedule.attendIds,
                attends: _schedule.attends,
                cancelReason: _schedule.cancelReason,
                contactName: _schedule.contactName,
                contactEmail: _schedule.contactEmail,
                contactPhone: _schedule.contactPhone,
                contactLineId: _schedule.contactLineId,
              );
            });
          }
        }
      } catch (e) {
        print('On-the-fly geocoding failed: $e');
      }
    }

    if (_schedule.latitude == null || _schedule.longitude == null) {
      print('No destination coordinates found');
      return;
    }

    try {
      final apiService = ApiService();
      // Fetch ALL estimates
      final allData = await apiService.estimateAllTravelTimes(
        position.latitude,
        position.longitude,
        _schedule.latitude!,
        _schedule.longitude!,
      );

      if (mounted) {
        setState(() {
          _allEstimates = allData;
          _updateSelectedMode(_selectedMode);
        });

        if (_isLate) {
          _showLateDialog();
        }
      }
    } catch (e) {
      print('Travel estimation error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not get travel time: $e')),
        );
      }
    } finally {
      // Ensure map fits bounds regardless of API success
      if (mounted &&
          _controller.isCompleted &&
          _schedule.latitude != null &&
          _schedule.longitude != null) {
        print(
          "DEBUG: Fitting bounds to current=${position.latitude},${position.longitude} and dest=${_schedule.latitude},${_schedule.longitude}",
        );
        final controller = await _controller.future;
        // Fit bounds logic...
        double minLat = position.latitude < _schedule.latitude!
            ? position.latitude
            : _schedule.latitude!;
        double maxLat = position.latitude > _schedule.latitude!
            ? position.latitude
            : _schedule.latitude!;
        double minLon = position.longitude < _schedule.longitude!
            ? position.longitude
            : _schedule.longitude!;
        double maxLon = position.longitude > _schedule.longitude!
            ? position.longitude
            : _schedule.longitude!;

        // Add some padding
        double latPadding = (maxLat - minLat) * 0.2;
        double lonPadding = (maxLon - minLon) * 0.2;

        // Avoid zero padding if points are identical
        if (latPadding == 0) latPadding = 0.01;
        if (lonPadding == 0) lonPadding = 0.01;

        try {
          controller.animateCamera(
            CameraUpdate.newLatLngBounds(
              LatLngBounds(
                southwest: LatLng(minLat - latPadding, minLon - lonPadding),
                northeast: LatLng(maxLat + latPadding, maxLon + lonPadding),
              ),
              50,
            ),
          );
        } catch (e) {
          print("Camera update error: $e");
        }
      }
    }
  }

  void _updateSelectedMode(String mode) {
    if (_allEstimates.containsKey(mode)) {
      final data = _allEstimates[mode];
      setState(() {
        _selectedMode = mode;
        _estimatedTravelTimeMinutes = (data['duration'] as double).round();

        final arrivalTime = DateTime.now().add(
          Duration(minutes: _estimatedTravelTimeMinutes!),
        );
        _isLate = arrivalTime.isAfter(_schedule.startTime);
      });
    }
  }

  Widget _buildAttendeeSection() {
    final attends = _schedule.attends;
    final hasAttends = attends != null && attends.isNotEmpty;

    String displayName;
    String? displayPhone;

    if (hasAttends) {
      final idx = _selectedAttendeeIndex.clamp(0, attends.length - 1);
      final selected = attends[idx];
      displayName = selected['nick_name'] ?? selected['name'] ?? selected['full_name'] ?? '';
      displayPhone = selected['phone'] as String?;
    } else {
      displayName = _schedule.contactName ?? '';
      displayPhone = _schedule.contactPhone;
    }

    if (displayName.isEmpty && (displayPhone == null || displayPhone.isEmpty)) {
      return SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(height: 4),
        // Chip selector when multiple attendees
        if (hasAttends && attends.length > 1) ...[
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: List.generate(attends.length, (i) {
                final name = attends[i]['nick_name'] ?? attends[i]['name'] ?? attends[i]['full_name'] ?? '?';
                final isSelected = i == _selectedAttendeeIndex;
                return GestureDetector(
                  onTap: () => setState(() => _selectedAttendeeIndex = i),
                  child: Container(
                    margin: EdgeInsets.only(right: 8),
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: isSelected ? Colors.grey[200] : Colors.grey[100],
                      border: Border.all(
                        color: isSelected ? Colors.black : Colors.grey[300]!,
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      name,
                      style: TextStyle(
                        color: isSelected ? Colors.black : Colors.grey[700],
                        fontSize: 13,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
          SizedBox(height: 6),
        ],
        // Name + Phone row
        Row(
          children: [
            Icon(Icons.person, size: 16, color: Colors.grey),
            SizedBox(width: 4),
            Expanded(
              child: Text(
                displayName,
                style: TextStyle(color: Colors.grey[700]),
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
              ),
            ),
            if (displayPhone != null && displayPhone.isNotEmpty) ...[
              SizedBox(width: 8),
              Icon(Icons.phone, size: 16, color: Colors.grey),
              SizedBox(width: 4),
              Text(
                displayPhone,
                style: TextStyle(color: Colors.grey[700]),
              ),
            ],
          ],
        ),
      ],
    );
  }

  void _showCancelDialog() {
    final reasonController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('cancelSchedule'.tr()),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_schedule.title,
                style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: reasonController,
              autofocus: true,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: 'cancelReason'.tr(),
                hintText: 'cancelReasonHint'.tr(),
                border: const OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('cancel'.tr()),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red,
                foregroundColor: Colors.white),
            onPressed: () async {
              if (reasonController.text.trim().isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('cancelReasonRequired'.tr())));
                return;
              }

              final dialogContext = context;
              Navigator.pop(dialogContext);
              try {
                final apiService = ApiService();
                await apiService.updateStatus(
                  _schedule.id,
                  ScheduleStatus.cancel,
                  cancelReason: reasonController.text.trim(),
                );

                if (!mounted) return;
                ScaffoldMessenger.of(this.context).showSnackBar(
                    SnackBar(content: Text('scheduleCancelled'.tr())));
                Navigator.pop(this.context, true);
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(this.context).showSnackBar(SnackBar(
                    content: Text('cancelFailed'.tr(
                        namedArgs: {'error': e.toString()}))));
              }
            },
            child: Text('confirm'.tr()),
          ),
        ],
      ),
    );
  }

  void _showLateDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Late Notification'),
        content: Text(
          'Estimated arrival time is after the schedule start time. Would you like to notify others?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Other users have been notified!')),
              );
            },
            child: Text('Notify'),
          ),
        ],
      ),
    );
  }

  void _editSchedule() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AddScheduleScreen(schedule: _schedule),
      ),
    );

    if (result != null && result is Schedule) {
      print(
        'DEBUG: MapScreen received update: ${result.latitude}, ${result.longitude}',
      );
      setState(() {
        _schedule = result;
        _selectedMode = _schedule.transportMode ?? 'car';
      });
      _checkLocationAndTravel(); // Refresh map and estimates
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('travelPlan'.tr()),
        actions: [IconButton(icon: Icon(Icons.edit), onPressed: _editSchedule)],
      ),
      body: Stack(
        children: [
          // MAP
          if (_currentPosition != null) ...[
            GoogleMap(
              initialCameraPosition: CameraPosition(
                target: LatLng(
                  _currentPosition!.latitude,
                  _currentPosition!.longitude,
                ),
                zoom: 14,
              ),
              onMapCreated: (GoogleMapController controller) {
                _controller.complete(controller);
              },
              markers: {
                Marker(
                  markerId: MarkerId('current'),
                  position: LatLng(
                    _currentPosition!.latitude,
                    _currentPosition!.longitude,
                  ),
                  infoWindow: InfoWindow(title: 'You'),
                  icon: BitmapDescriptor.defaultMarkerWithHue(
                    BitmapDescriptor.hueBlue,
                  ),
                ),
                if (_schedule.latitude != null && _schedule.longitude != null)
                  Marker(
                    markerId: MarkerId('destination'),
                    position: LatLng(_schedule.latitude!, _schedule.longitude!),
                    infoWindow: InfoWindow(
                      title: _schedule.location ?? 'Destination',
                    ),
                    icon: BitmapDescriptor.defaultMarkerWithHue(
                      BitmapDescriptor.hueRed,
                    ),
                  ),
              },
              padding: const EdgeInsets.only(
                bottom: 380, // Match the bottom sheet height exactly to center the map properly above it
              ),
            ),
              
            // Custom Map Controls (since native ones may not show on Web)
            // My Location Button (Bottom Right)
            Positioned(
              right: 16,
              bottom: 400, // 380 (sheet height) + 20 (padding)
              child: FloatingActionButton(
                heroTag: "btn_my_location",
                mini: true,
                backgroundColor: Colors.white,
                child: Icon(Icons.my_location, color: Colors.black87),
                onPressed: () async {
                  if (_controller.isCompleted && _currentPosition != null) {
                    final controller = await _controller.future;
                    controller.animateCamera(
                      CameraUpdate.newLatLng(
                        LatLng(_currentPosition!.latitude, _currentPosition!.longitude)
                      )
                    );
                  }
                },
              ),
            ),
            
            // Zoom Controls (Bottom Left)
            Positioned(
              left: 16,
              bottom: 400, // 380 (sheet height) + 20 (padding)
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  FloatingActionButton(
                    heroTag: "btn_zoom_in",
                    mini: true,
                    backgroundColor: Colors.white,
                    child: Icon(Icons.add, color: Colors.black87),
                    onPressed: () async {
                      if (_controller.isCompleted) {
                        final controller = await _controller.future;
                        controller.animateCamera(CameraUpdate.zoomIn());
                      }
                    },
                  ),
                  SizedBox(height: 8),
                  FloatingActionButton(
                    heroTag: "btn_zoom_out",
                    mini: true,
                    backgroundColor: Colors.white,
                    child: Icon(Icons.remove, color: Colors.black87),
                    onPressed: () async {
                      if (_controller.isCompleted) {
                        final controller = await _controller.future;
                        controller.animateCamera(CameraUpdate.zoomOut());
                      }
                    },
                  ),
                ],
              ),
            ),
          ] else
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (_schedule.latitude == null || _schedule.longitude == null)
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Text(
                        'Location not set. Please edit the schedule to set a location.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.red),
                      ),
                    ),
                  if (_currentPosition == null) CircularProgressIndicator(),
                ],
              ),
            ),

          // BOTTOM SHEET
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 380, // Increased height for sheet
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 10)],
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _schedule.title,
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    _buildAttendeeSection(),
                    SizedBox(height: 8),

                    // Mode Selection Row
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: _allEstimates.isEmpty
                          ? Padding(
                              padding: EdgeInsets.all(8),
                              child: Text("Loading estimates..."),
                            )
                          : Row(
                              children: ['car', 'motorcycle', 'bus', 'walk']
                                  .map((mode) {
                                    final data = _allEstimates[mode];
                                    final duration = data != null
                                        ? (data['duration'] as double).round()
                                        : '--';
                                    final isSelected = _selectedMode == mode;

                                    IconData icon;
                                    switch (mode) {
                                      case 'car':
                                        icon = Icons.directions_car;
                                        break;
                                      case 'motorcycle':
                                        icon = Icons.two_wheeler;
                                        break;
                                      case 'bus':
                                        icon = Icons.directions_bus;
                                        break;
                                      case 'walk':
                                        icon = Icons.directions_walk;
                                        break;
                                      default:
                                        icon = Icons.help;
                                    }

                                    return GestureDetector(
                                      onTap: () => _updateSelectedMode(mode),
                                      child: Container(
                                        margin: EdgeInsets.only(right: 12),
                                        padding: EdgeInsets.symmetric(
                                          horizontal: 16,
                                          vertical: 12,
                                        ),
                                        decoration: BoxDecoration(
                                          color: isSelected
                                              ? Colors.grey[200]
                                              : Colors.grey[100],
                                          border: Border.all(
                                            color: isSelected
                                                ? Colors.black
                                                : Colors.transparent,
                                          ),
                                          borderRadius: BorderRadius.circular(
                                            12,
                                          ),
                                        ),
                                        child: Column(
                                          children: [
                                            Icon(
                                              icon,
                                              color: isSelected
                                                  ? Colors.black
                                                  : Colors.grey,
                                            ),
                                            SizedBox(height: 4),
                                            Text(
                                              '${duration} min',
                                              style: TextStyle(
                                                fontWeight: FontWeight.bold,
                                                color: isSelected
                                                    ? Colors.black
                                                    : Colors.black,
                                              ),
                                            ),
                                            Text(
                                              mode,
                                              style: TextStyle(
                                                fontSize: 10,
                                                color: Colors.grey,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    );
                                  })
                                  .toList(),
                            ),
                    ),

                    Divider(height: 24),

                    // Status Row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'estimatedArrival'.tr(),
                              style: TextStyle(
                                color: Colors.grey,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              _estimatedTravelTimeMinutes != null
                                  ? DateTime.now()
                                        .add(
                                          Duration(
                                            minutes:
                                                _estimatedTravelTimeMinutes!,
                                          ),
                                        )
                                        .toString()
                                        .substring(11, 16)
                                  : '--:--',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              'status'.tr(),
                              style: TextStyle(
                                color: Colors.grey,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              _isLate ? 'runningLate'.tr() : 'onTime'.tr(),
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: _isLate ? Colors.red : Colors.green,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),

                    if (_isLate &&
                        _schedule.status != ScheduleStatus.cancel) ...[
                      SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          icon: Icon(Icons.notifications),
                          label: Text('notifyOthers'.tr()),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red,
                            foregroundColor: Colors.white,
                          ),
                          onPressed: _showLateDialog,
                        ),
                      ),
                    ],

                    if (_schedule.status != ScheduleStatus.cancel) ...[
                      SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          icon: Icon(Icons.cancel),
                          label: Text('cancelSchedule'.tr()),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.red,
                          ),
                          onPressed: _showCancelDialog,
                        ),
                      ),
                    ] else ...[
                      SizedBox(height: 12),
                      Text(
                        'cancelledLabel'.tr(namedArgs: {'reason': _schedule.cancelReason ?? 'noReason'.tr()}),
                        style: TextStyle(
                          color: Colors.red,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          icon: Icon(Icons.restore),
                          label: Text('restoreSchedule'.tr()),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.grey[200],
                            foregroundColor: Colors.black,
                          ),
                          onPressed: () async {
                            final messenger = ScaffoldMessenger.of(context);
                            try {
                              final apiService = ApiService();
                              await apiService.updateStatus(
                                _schedule.id,
                                ScheduleStatus.pending,
                              );
                              if (!mounted) return;
                              setState(() {
                                _schedule = Schedule(
                                  id: _schedule.id,
                                  title: _schedule.title,
                                  description: _schedule.description,
                                  startTime: _schedule.startTime,
                                  endTime: _schedule.endTime,
                                  location: _schedule.location,
                                  latitude: _schedule.latitude,
                                  longitude: _schedule.longitude,
                                  status: ScheduleStatus.pending,
                                  transportMode: _schedule.transportMode,
                                  attendIds: _schedule.attendIds,
                                  cancelReason: null,
                                  contactName: _schedule.contactName,
                                  contactEmail: _schedule.contactEmail,
                                  contactPhone: _schedule.contactPhone,
                                  contactLineId: _schedule.contactLineId,
                                );
                              });
                              messenger.showSnackBar(
                                SnackBar(content: Text('scheduleRestored'.tr())),
                              );
                            } catch (e) {
                              messenger.showSnackBar(
                                SnackBar(content: Text('restoreFailed'.tr(
                                    namedArgs: {'error': e.toString()}))),
                              );
                            }
                          },
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
