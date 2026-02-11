import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import "../l10n/app_localizations.dart";

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

  @override
  void initState() {
    super.initState();
    if (widget.initialLat != null && widget.initialLon != null) {
      _pickedLocation = LatLng(widget.initialLat!, widget.initialLon!);
      _markers.add(
        Marker(
          markerId: MarkerId('picked'),
          position: _pickedLocation!,
        ),
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

  void _onMapTapped(LatLng position) {
    setState(() {
      _pickedLocation = position;
      _markers.clear();
      _markers.add(
        Marker(
          markerId: MarkerId('picked'),
          position: position,
        ),
      );
    });
  }

  void _confirmSelection() {
    if (_pickedLocation != null) {
      Navigator.pop(context, {
        "latitude": _pickedLocation!.latitude,
        "longitude": _pickedLocation!.longitude,
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.selectLocation ?? 'Select Location'),
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
              target: _pickedLocation ?? LatLng(25.0330, 121.5654), // Default Taipei 101
              zoom: 15,
            ),
            onMapCreated: (controller) => _controller = controller,
            onTap: _onMapTapped,
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
                  AppLocalizations.of(context)!.confirm ?? 'Confirm Location',
                  style: TextStyle(fontSize: 18),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
