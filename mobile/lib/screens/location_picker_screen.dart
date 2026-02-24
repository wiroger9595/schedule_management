import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import '../i18n/app_localizations.dart';
import 'dart:async';
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

  LatLng? _currentCameraPosition; // Track camera center
  double _currentZoom = 15.0; // Track zoom level



  @override
  void initState() {
    super.initState();
    if (widget.initialLat != null && widget.initialLon != null) {
      _pickedLocation = LatLng(widget.initialLat!, widget.initialLon!);
      _markers.add(
        Marker(markerId: MarkerId('picked'), position: _pickedLocation!),
      );
      _currentCameraPosition = _pickedLocation;
    } else {
      _currentCameraPosition = LatLng(25.0330, 121.5654); // Default to Taipei 101
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
      final latLng = LatLng(position.latitude, position.longitude);
      _currentCameraPosition = latLng; // Update current pos
      _controller!.animateCamera(
        CameraUpdate.newCameraPosition(
          CameraPosition(
            target: latLng,
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
  void dispose() {
    super.dispose();
  }

  void _selectLocation(LatLng pos, String name, String address) {
      setState(() {
         _pickedLocation = pos;
         _pickedPlaceName = name;
         _markers.clear();
         _markers.add(
            Marker(
               markerId: MarkerId('picked'),
               position: pos,
            ),
         );
      });
      _controller?.animateCamera(CameraUpdate.newLatLng(pos));
  }

  void _zoomIn() {
    if (_controller != null) {
      _controller!.animateCamera(CameraUpdate.zoomIn());
    }
  }

  void _zoomOut() {
    if (_controller != null) {
      _controller!.animateCamera(CameraUpdate.zoomOut());
    }
  }

  void _showSearchOverlay() {
     showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => _SearchOverlay(
           initialQuery: '',
           currentCameraPosition: _currentCameraPosition,
           currentZoom: _currentZoom,
           onSelect: (Map<String, dynamic> place) {
              if (place['lat'] != null && place['lon'] != null) {
                 final lat = place['lat'] as double;
                 final lon = place['lon'] as double;
                 final pos = LatLng(lat, lon);
                 _selectLocation(pos, place['name'], place['address'] ?? '');
                 Navigator.pop(context); // Close the sheet
              }
           },
        ),
     );
  }

  void _onMapCreated(GoogleMapController controller) {
    _controller = controller;
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
            onMapCreated: _onMapCreated,
            initialCameraPosition: CameraPosition(
              target: _pickedLocation ?? LatLng(25.0330, 121.5654),
              zoom: 15,
            ),
            markers: _markers,
            myLocationEnabled: true,
            myLocationButtonEnabled: false, // Custom button below
            zoomControlsEnabled: false, // Custom controls below
            onCameraMove: (CameraPosition position) {
              _currentCameraPosition = position.target;
              _currentZoom = position.zoom;
            },
            onCameraIdle: () {
              // Ensure we capture the final position when movement stops
              if (_controller != null) {
                 _controller!.getVisibleRegion().then((bounds) {
                    final center = LatLng(
                      (bounds.northeast.latitude + bounds.southwest.latitude) / 2,
                      (bounds.northeast.longitude + bounds.southwest.longitude) / 2,
                    );
                    _currentCameraPosition = center;
                 });
              }
            },
            onTap: (LatLng pos) {
               _onMapTapped(pos);
            },
          ),
          


          // Bottom Info Sheet (if location selected)
          if (_pickedLocation != null)
             Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                child: Container(
                   padding: EdgeInsets.all(20),
                   decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
                      boxShadow: [
                         BoxShadow(color: Colors.black12, blurRadius: 10, offset: Offset(0, -2)),
                      ],
                   ),
                   child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                         Text(
                            _pickedPlaceName ?? 'Selected Location',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                         ),
                         SizedBox(height: 8),
                         Text(
                            '${_pickedLocation!.latitude.toStringAsFixed(5)}, ${_pickedLocation!.longitude.toStringAsFixed(5)}',
                            style: TextStyle(color: Colors.grey[600]),
                         ),
                         SizedBox(height: 16),
                         SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                               onPressed: () {
                                  Navigator.pop(context, {
                                     'address': _pickedPlaceName ?? 'Selected Location',
                                     'latitude': _pickedLocation!.latitude,
                                     'longitude': _pickedLocation!.longitude,
                                  });
                               },
                               child: Text('Confirm Location'),
                            ),
                         ),
                         SizedBox(height: 20), // Bottom padding
                      ],
                   ),
                ),
             ),
             
          // Current Location Button
          Positioned(
             right: 16,
             bottom: _pickedLocation != null ? 180 : 30, // Adjust based on bottom sheet
             child: FloatingActionButton(
                heroTag: "my_location",
                mini: true,
                backgroundColor: Colors.white,
                foregroundColor: Colors.black,
                child: Icon(Icons.my_location),
                onPressed: _determinePosition,
             ),
          ),
          
          // Zoom Controls (Left side)
          Positioned(
            left: 16,
            bottom: _pickedLocation != null ? 180 : 30,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                FloatingActionButton(
                  heroTag: "zoom_in",
                  mini: true,
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.black,
                  child: Icon(Icons.add),
                  onPressed: _zoomIn,
                ),
                SizedBox(height: 8),
                FloatingActionButton(
                  heroTag: "zoom_out",
                  mini: true,
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.black,
                  child: Icon(Icons.remove),
                  onPressed: _zoomOut,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// Search Overlay with Autocomplete-style behavior
class _SearchOverlay extends StatefulWidget {
  final String initialQuery;
  final LatLng? currentCameraPosition;
  final double currentZoom;
  final Function(Map<String, dynamic>) onSelect;

  const _SearchOverlay({
    Key? key,
    required this.initialQuery,
    this.currentCameraPosition,
    required this.currentZoom,
    required this.onSelect,
  }) : super(key: key);

  @override
  __SearchOverlayState createState() => __SearchOverlayState();
}

class __SearchOverlayState extends State<_SearchOverlay> {
  final TextEditingController _searchController = TextEditingController();
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _searchResults = [];
  bool _isLoading = false;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _searchController.text = widget.initialQuery;
    // If initial query is present, search immediately
    if (widget.initialQuery.isNotEmpty) {
      _performSearch(widget.initialQuery);
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    _debounce = Timer(const Duration(milliseconds: 1000), () {
      _performSearch(query);
    });
  }

  Future<void> _performSearch(String query) async {
    // Filter out incomplete Bopomofo (Zhuyin) input
    // U+3100-U+312F (Bopomofo) & U+31A0-U+31BF (Bopomofo Extended)
    if (RegExp(r'[\u3100-\u312F\u31A0-\u31BF]').hasMatch(query)) {
      return;
    }

    if (query.isEmpty) {
      if (mounted) {
        setState(() {
          _searchResults = [];
          _isLoading = false;
        });
      }
      return;
    }

    if (mounted) {
      setState(() {
        _isLoading = true;
      });
    }

    try {
      final lat = widget.currentCameraPosition?.latitude;
      final lon = widget.currentCameraPosition?.longitude;
      // Search with current map center bias
      final results = await _apiService.searchPlaces(query, lat, lon, zoom: widget.currentZoom);
      
      if (mounted) {
        setState(() {
          _searchResults = results;
          _isLoading = false;
        });
      }
    } catch (e) {
      print("Search failed: $e");
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Search failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.9,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            boxShadow: [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 10,
                offset: Offset(0, -2),
              )
            ],
          ),
          child: Column(
            children: [
              // Handle bar
              Container(
                width: 40,
                height: 5,
                margin: EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              
              // Search Input Area
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                child: Row(
                   children: [
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          autofocus: true,
                          decoration: InputDecoration(
                            hintText: 'Search for a place...',
                            prefixIcon: Icon(Icons.search),
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: Icon(Icons.clear),
                                    onPressed: () {
                                      _searchController.clear();
                                      _performSearch('');
                                    },
                                  )
                                : null,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide.none,
                            ),
                            filled: true,
                            fillColor: Colors.grey[100],
                            contentPadding: EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                          ),
                          onChanged: _onSearchChanged,
                          onSubmitted: _performSearch,
                        ),
                      ),
                      SizedBox(width: 8),
                      TextButton(
                         onPressed: () => Navigator.pop(context),
                         child: Text("Cancel"),
                      )
                   ],
                ),
              ),
              Divider(height: 1),

              // Results List
              Expanded(
                child: _isLoading
                    ? Center(child: CircularProgressIndicator())
                    : _searchResults.isEmpty
                        ? Center(
                            child: Text(
                              _searchController.text.isEmpty
                                  ? 'Type to search'
                                  : 'No results found',
                              style: TextStyle(color: Colors.grey),
                            ),
                          )
                        : ListView.separated(
                            controller: scrollController,
                            itemCount: _searchResults.length,
                            separatorBuilder: (context, index) => Divider(height: 1),
                            itemBuilder: (context, index) {
                              final place = _searchResults[index];
                              return ListTile(
                                leading: Container(
                                   padding: EdgeInsets.all(8),
                                   decoration: BoxDecoration(
                                      color: Colors.blue[50], // Soft blue bg
                                      shape: BoxShape.circle,
                                   ),
                                   child: Icon(Icons.place, color: Colors.blue),
                                ),
                                title: Text(place['name'] ?? '', style: TextStyle(fontWeight: FontWeight.w600)),
                                subtitle: Text(place['address'] ?? '', maxLines: 1, overflow: TextOverflow.ellipsis),
                                onTap: () {
                                  widget.onSelect(place);
                                },
                              );
                            },
                          ),
              ),
            ],
          ),
        );
      },
    );
  }
}
