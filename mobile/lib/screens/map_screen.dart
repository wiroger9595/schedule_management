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

  void _showCancelDialog() {
    final reasonController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Cancel Schedule'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Are you sure you want to cancel this schedule?'),
            SizedBox(height: 8),
            TextField(
              controller: reasonController,
              decoration: InputDecoration(
                labelText: 'Reason',
                hintText: 'e.g. Sick, Emergency',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Back'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () async {
              if (reasonController.text.isEmpty) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Reason is required')));
                return;
              }

              Navigator.pop(context);
              try {
                final apiService = ApiService();
                await apiService.updateStatus(
                  _schedule.id,
                  ScheduleStatus.cancel,
                  cancelReason: reasonController.text,
                );

                setState(() {
                  // We need to update local schedule object to reflect change immediately
                  // But schedule is final, so we might need to refetch or create new instance
                  // For now, let's just pop back or refresh?
                  // Better to refresh the map screen state.
                  // Actually MapScreen takes schedule as param.
                });

                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Schedule cancelled')));
                Navigator.pop(
                  context,
                  true,
                ); // Return true to trigger refresh in HomeScreen
              } catch (e) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Failed to cancel: $e')));
              }
            },
            child: Text(
              'Confirm Cancel',
              style: TextStyle(color: Colors.white),
            ),
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
        title: Text('Travel Plan'),
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
            Positioned(
              right: 16,
              bottom: 400, // 380 (sheet height) + 20 (padding)
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  FloatingActionButton(
                    heroTag: "btn_my_location",
                    mini: true,
                    backgroundColor: Colors.white,
                    child: Icon(Icons.my_location, color: Colors.blue),
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
                  SizedBox(height: 12),
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
                    if (_schedule.contactName != null &&
                        _schedule.contactName!.isNotEmpty) ...[
                      SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(Icons.person, size: 16, color: Colors.grey),
                          SizedBox(width: 4),

                          // 關鍵修正：使用 Expanded 加上 ellipsis
                          Expanded(
                            child: Text(
                              _schedule.contactName!,
                              style: TextStyle(color: Colors.grey[700]),
                              overflow: TextOverflow.ellipsis, // 超出長度顯示 ...
                              maxLines: 1, // 限制只有一行
                            ),
                          ),

                          // 電話部分
                          if (_schedule.contactPhone != null &&
                              _schedule.contactPhone!.isNotEmpty) ...[
                            SizedBox(width: 8),
                            Icon(Icons.phone, size: 16, color: Colors.grey),
                            SizedBox(width: 4),
                            // 電話號碼通常長度固定，可以直接顯示
                            Text(
                              _schedule.contactPhone!,
                              style: TextStyle(color: Colors.grey[700]),
                            ),
                          ],
                        ],
                      ),
                    ],
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
                                              ? Colors.blue[50]
                                              : Colors.grey[100],
                                          border: Border.all(
                                            color: isSelected
                                                ? Colors.blue
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
                                                  ? Colors.blue
                                                  : Colors.grey,
                                            ),
                                            SizedBox(height: 4),
                                            Text(
                                              '${duration} min',
                                              style: TextStyle(
                                                fontWeight: FontWeight.bold,
                                                color: isSelected
                                                    ? Colors.blue
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
                              'Estimated Arrival',
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
                              'Status',
                              style: TextStyle(
                                color: Colors.grey,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              _isLate ? 'Running Late' : 'On Time',
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
                          label: Text('Notify Others'),
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
                          label: Text('Cancel Schedule'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.red,
                          ),
                          onPressed: _showCancelDialog,
                        ),
                      ),
                    ] else ...[
                      SizedBox(height: 12),
                      Text(
                        'Cancelled: ${_schedule.cancelReason ?? "No reason"}',
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
                          label: Text('Restore Schedule'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.grey[200],
                            foregroundColor: Colors.black,
                          ),
                          onPressed: () async {
                            try {
                              final apiService = ApiService();
                              await apiService.updateStatus(
                                _schedule.id,
                                ScheduleStatus.pending,
                                cancelReason:
                                    null, // Clear reason? API might ignore nulls if not explicit.
                              );
                              // API updateStatus logic: if cancelReason is not in dict, it's not updated.
                              // But `updateStatus` in ApiService takes `cancelReason` and puts it in if not null.
                              // If I want to clear it, I might need to send empty string or handle it in backend.
                              // For now, just changing status to PENDING is enough to "restore" it.

                              setState(() {
                                // Optimistically update
                                _schedule = Schedule(
                                  id: _schedule.id,
                                  title: _schedule.title,
                                  description: _schedule.description,
                                  startTime: _schedule.startTime,
                                  endTime: _schedule.endTime,
                                  location: _schedule.location,
                                  latitude: _schedule.latitude,
                                  longitude: _schedule.longitude,
                                  status:
                                      ScheduleStatus.pending, // Back to pending
                                  transportMode: _schedule.transportMode,
                                  attendIds: _schedule.attendIds,
                                  cancelReason: _schedule
                                      .cancelReason, // Keep reason for history or clear it?
                                  contactName: _schedule.contactName,
                                  contactEmail: _schedule.contactEmail,
                                  contactPhone: _schedule.contactPhone,
                                  contactLineId: _schedule.contactLineId,
                                );
                              });
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Schedule restored')),
                              );
                            } catch (e) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('Failed to restore: $e'),
                                ),
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
