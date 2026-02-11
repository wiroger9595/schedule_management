import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:async';
import 'dart:convert';
import '../models/schedule.dart';
import '../services/api_service.dart';
import 'add_schedule_screen.dart';

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
       if (mounted && _controller.isCompleted && _schedule.latitude != null && _schedule.longitude != null) {
            print("DEBUG: Fitting bounds to current=${position.latitude},${position.longitude} and dest=${_schedule.latitude},${_schedule.longitude}");
            final controller = await _controller.future;
            // Fit bounds logic...
            double minLat = position.latitude < _schedule.latitude! ? position.latitude : _schedule.latitude!;
            double maxLat = position.latitude > _schedule.latitude! ? position.latitude : _schedule.latitude!;
            double minLon = position.longitude < _schedule.longitude! ? position.longitude : _schedule.longitude!;
            double maxLon = position.longitude > _schedule.longitude! ? position.longitude : _schedule.longitude!;
            
            // Add some padding
            double latPadding = (maxLat - minLat) * 0.2;
            double lonPadding = (maxLon - minLon) * 0.2;
            
            // Avoid zero padding if points are identical
            if (latPadding == 0) latPadding = 0.01;
            if (lonPadding == 0) lonPadding = 0.01;

            try {
              controller.animateCamera(CameraUpdate.newLatLngBounds(
                LatLngBounds(
                  southwest: LatLng(minLat - latPadding, minLon - lonPadding),
                  northeast: LatLng(maxLat + latPadding, maxLon + lonPadding),
                ),
                50,
              ));
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
         
         final arrivalTime = DateTime.now().add(Duration(minutes: _estimatedTravelTimeMinutes!));
         _isLate = arrivalTime.isAfter(_schedule.startTime);
       });
    }
  }

  void _showLateDialog() {
     showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Late Notification'),
        content: Text('Estimated arrival time is after the schedule start time. Would you like to notify others?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text('Cancel')),
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
      print('DEBUG: MapScreen received update: ${result.latitude}, ${result.longitude}');
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
        actions: [
          IconButton(
            icon: Icon(Icons.edit),
            onPressed: _editSchedule,
          ),
        ],
      ),
      body: Stack(
        children: [
          // MAP
          if (_currentPosition != null)
            GoogleMap(
              initialCameraPosition: CameraPosition(
                target: LatLng(_currentPosition!.latitude, _currentPosition!.longitude),
                zoom: 14,
              ),
              onMapCreated: (GoogleMapController controller) {
                _controller.complete(controller);
              },
              markers: {
                Marker(
                  markerId: MarkerId('current'),
                  position: LatLng(_currentPosition!.latitude, _currentPosition!.longitude),
                  infoWindow: InfoWindow(title: 'You'),
                  icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueBlue),
                ),
                if (_schedule.latitude != null && _schedule.longitude != null)
                  Marker(
                    markerId: MarkerId('destination'),
                    position: LatLng(_schedule.latitude!, _schedule.longitude!),
                    infoWindow: InfoWindow(title: _schedule.location ?? 'Destination'),
                    icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed),
                  ),
              },
              padding: EdgeInsets.only(bottom: 250), // Make space for bottom sheet
            )
          else
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
                   if (_currentPosition == null)
                     CircularProgressIndicator(),
                ],
              ),
            ),
          
          // BOTTOM SHEET
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              height: 280, // Fixed height for sheet
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 10)],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                   Text(_schedule.title, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                   SizedBox(height: 8),
                   
                   // Mode Selection Row
                   SingleChildScrollView(
                     scrollDirection: Axis.horizontal,
                     child: _allEstimates.isEmpty 
                     ? Padding(padding: EdgeInsets.all(8), child: Text("Loading estimates..."))
                     : Row(
                       children: ['car', 'motorcycle', 'bus', 'walk'].map((mode) {
                          final data = _allEstimates[mode];
                          final duration = data != null ? (data['duration'] as double).round() : '--';
                          final isSelected = _selectedMode == mode;
                          
                          IconData icon;
                          switch(mode) {
                            case 'car': icon = Icons.directions_car; break;
                            case 'motorcycle': icon = Icons.two_wheeler; break;
                            case 'bus': icon = Icons.directions_bus; break;
                            case 'walk': icon = Icons.directions_walk; break;
                            default: icon = Icons.help;
                          }

                          return GestureDetector(
                            onTap: () => _updateSelectedMode(mode),
                            child: Container(
                              margin: EdgeInsets.only(right: 12),
                              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                              decoration: BoxDecoration(
                                color: isSelected ? Colors.blue[50] : Colors.grey[100],
                                border: Border.all(color: isSelected ? Colors.blue : Colors.transparent),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Column(
                                children: [
                                  Icon(icon, color: isSelected ? Colors.blue : Colors.grey),
                                  SizedBox(height: 4),
                                  Text('${duration} min', style: TextStyle(fontWeight: FontWeight.bold, color: isSelected ? Colors.blue : Colors.black)),
                                  Text(mode, style: TextStyle(fontSize: 10, color: Colors.grey)),
                                ],
                              ),
                            ),
                          );
                       }).toList(),
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
                          Text('Estimated Arrival', style: TextStyle(color: Colors.grey, fontSize: 12)),
                          Text(
                            _estimatedTravelTimeMinutes != null 
                             ? DateTime.now().add(Duration(minutes: _estimatedTravelTimeMinutes!)).toString().substring(11, 16)
                             : '--:--', 
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)
                          ),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text('Status', style: TextStyle(color: Colors.grey, fontSize: 12)),
                          Text(
                            _isLate ? 'Running Late' : 'On Time',
                            style: TextStyle(
                              fontSize: 18, 
                              fontWeight: FontWeight.bold,
                              color: _isLate ? Colors.red : Colors.green
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  
                  if (_isLate) ...[
                    SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: Icon(Icons.notifications),
                        label: Text('Notify Others'),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
                        onPressed: _showLateDialog,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
