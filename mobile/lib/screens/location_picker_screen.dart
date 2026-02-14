import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import '../i18n/app_localizations.dart';
import '../services/api_service.dart';

class LocationPickerScreen extends StatefulWidget {
  final double? initialLat;
  final double? initialLon;

  LocationPickerScreen({this.initialLat, this.initialLon});

  @override
  _LocationPickerScreenState createState() => _LocationPickerScreenState();
}

class _LocationPickerScreenState extends State<LocationPickerScreen> {
  GoogleMapController? _controller;
  LatLng? _pickedLocation;
  Set<Marker> _markers = {};
  String? _pickedPlaceName;
  final ApiService _apiService = ApiService();

  @override
  void initState() {
    super.initState();
    if (widget.initialLat != null && widget.initialLon != null) {
      _pickedLocation = LatLng(widget.initialLat!, widget.initialLon!);
      _markers.add(
        Marker(markerId: MarkerId('picked'), position: _pickedLocation!),
      );
    } else {
      _determinePosition();
    }
  }

  Future<void> _determinePosition() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return;

    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }

    if (permission == LocationPermission.deniedForever) return;

    Position position = await Geolocator.getCurrentPosition();

    if (mounted && _controller != null) {
      _controller!.animateCamera(
        CameraUpdate.newCameraPosition(
          CameraPosition(
            target: LatLng(position.latitude, position.longitude),
            zoom: 15,
          ),
        ),
      );
    }
  }

  void _onMapTapped(LatLng position) async {
    setState(() {
      _pickedLocation = position;
      _pickedPlaceName = null; // Reset
      _markers.clear();
      _markers.add(Marker(markerId: MarkerId('picked'), position: position));
    });

    // Try to find a nearby POI
    try {
      final places = await _apiService.getNearbyPlaces(position.latitude, position.longitude);
      if (places.isNotEmpty && mounted) {
        // Sort by distance is handled by backend, so first is closest
        final closest = places.first;
        // Check if it's close enough to be considered a "click" on it. 
        // Backend returns distance in meters.
        // Let's say if within 50 meters, we suggest it.
        final distance = closest['distance'] as num;
        if (distance < 50) {
            final name = closest['name'];
            setState(() {
              _pickedPlaceName = name;
              _markers.add(
                Marker(
                  markerId: MarkerId('picked'),
                  position: position,
                  infoWindow: InfoWindow(title: name, snippet: 'Tap check to select'),
                ),
              );
            });
            _controller?.showMarkerInfoWindow(MarkerId('picked'));
            
            ScaffoldMessenger.of(context).hideCurrentSnackBar();
            ScaffoldMessenger.of(context).showSnackBar(
               SnackBar(
                 content: Text('Selected: $name'),
                 duration: Duration(seconds: 2),
               ),
            );
        }
      }
    } catch (e) {
      // Ignore errors for silent background check
      print("Error fetching nearby POI on tap: $e");
    }
  }

  void _confirmSelection() {
    if (_pickedLocation != null) {
      Navigator.pop(context, {
        "latitude": _pickedLocation!.latitude,
        "longitude": _pickedLocation!.longitude,
        "name": _pickedPlaceName,
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          AppLocalizations.of(context)!.selectLocation ?? 'Select Location',
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.check),
            onPressed: _pickedLocation == null ? null : _confirmSelection,
          ),
        ],
      ),
      body: Stack(
        children: [
          GoogleMap(
            initialCameraPosition: CameraPosition(
              target:
                  _pickedLocation ??
                  LatLng(25.0330, 121.5654), // Default Taipei 101
              zoom: 15,
            ),
            onMapCreated: (controller) => _controller = controller,
            onTap: _onMapTapped,
            // onPoiClick removed as it is not supported in this version
            markers: _markers,
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
          ),
          if (_pickedLocation != null)
            Positioned(
              bottom: 30,
              left: 20,
              right: 20,
              child: ElevatedButton(
                onPressed: _confirmSelection,
                style: ElevatedButton.styleFrom(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                ),
                child: Text(
                  _pickedPlaceName != null 
                      ? 'Confirm: $_pickedPlaceName' 
                      : (AppLocalizations.of(context)!.confirm ?? 'Confirm Location'),
                  style: TextStyle(fontSize: 18),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
