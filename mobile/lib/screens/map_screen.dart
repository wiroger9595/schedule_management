import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:async';
import 'dart:convert';
import '../models/schedule.dart';
import '../services/api_service.dart';

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

  @override
  void initState() {
    super.initState();
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
    setState(() {
      _currentPosition = position;
    });

    try {
        final apiService = ApiService();
        final headers = await apiService.getHeaders();
        final response = await http.get(
          Uri.parse('${ApiService.baseUrl.replaceAll('/api', '')}/api/estimate?lat1=${position.latitude}&lon1=${position.longitude}&lat2=25.0330&lon2=121.5654&mode=${widget.schedule.transportMode}'),
          headers: headers,
        );
        
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          setState(() {
            _estimatedTravelTimeMinutes = (data['duration'] as double).round();
            
            final arrivalTime = DateTime.now().add(Duration(minutes: _estimatedTravelTimeMinutes!));
            _isLate = arrivalTime.isAfter(widget.schedule.startTime);
          });
          
          if (_isLate) {
            _showLateDialog();
          }
        }
    } catch (e) {
      print('Travel estimation error: $e');
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Travel Plan')),
      body: Stack(
        children: [
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
                ),
              },
            )
          else
            Center(child: CircularProgressIndicator()),
          
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              padding: EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 10)],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(widget.schedule.title, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  Text(widget.schedule.location ?? 'No location set', style: TextStyle(color: Colors.grey)),
                  SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        children: [
                          Text('Travel Time', style: TextStyle(color: Colors.grey, fontSize: 12)),
                          Text('${_estimatedTravelTimeMinutes ?? "--"} mins', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      Column(
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
                    SizedBox(height: 16),
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
