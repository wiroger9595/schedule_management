import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';
import '../utils/constants.dart'; // Import constants
import 'package:home_widget/home_widget.dart';
import '../widgets/contact_picker.dart';
import '../widgets/attendee_selector.dart';
import '../i18n/app_localizations.dart';
import 'location_picker_screen.dart';

class AddScheduleScreen extends StatefulWidget {
  final Schedule? schedule;

  AddScheduleScreen({this.schedule});

  @override
  _AddScheduleScreenState createState() => _AddScheduleScreenState();
}

class _AddScheduleScreenState extends State<AddScheduleScreen> {
  final _formKey = GlobalKey<FormState>();
  final ApiService apiService = ApiService();

  List<Map<String, dynamic>> selectedContacts = [];

  DateTime startTime = DateTime.now().add(Duration(hours: 1));
  DateTime? endTime;
  String? location;
  String transportMode = 'car';
  double? latitude;
  double? longitude;

  final TextEditingController _locationController = TextEditingController();
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _contactNameController = TextEditingController();
  final TextEditingController _contactEmailController = TextEditingController();
  final TextEditingController _contactPhoneController = TextEditingController();
  final TextEditingController _contactLineIdController =
      TextEditingController();

  final List<Map<String, String>> transportModes = [
    {'value': 'car', 'label': '汽車'},
    {'value': 'motorcycle', 'label': '機車'},
    {'value': 'transit', 'label': '大眾運輸 (TDX)'},
    {'value': 'bike', 'label': '腳踏車'},
    {'value': 'walk', 'label': '行走'},
  ];

  @override
  void initState() {
    super.initState();
    if (widget.schedule != null) {
      final s = widget.schedule!;
      startTime = s.startTime;
      endTime = s.endTime;
      location = s.location;
      transportMode = s.transportMode ?? 'car';
      latitude = s.latitude;
      longitude = s.longitude;
      _locationController.text = location ?? '';
      _titleController.text = s.title;
      _descriptionController.text = s.description ?? '';
      _contactNameController.text = s.contactName ?? '';
      _contactEmailController.text = s.contactEmail ?? '';
      _contactPhoneController.text = s.contactPhone ?? '';
      _contactLineIdController.text = s.contactLineId ?? '';

      if (s.attends != null) {
        selectedContacts = List<Map<String, dynamic>>.from(s.attends!);
      } else if (s.contactName != null) {
        // Backward compatibility: create a guest/contact from legacy fields
        selectedContacts = [
          {
            'name': s.contactName,
            'email': s.contactEmail,
            'phone': s.contactPhone,
            'line_id': s.contactLineId,
            'type':
                'guest', // Assume guest if no ID, but we don't have ID here easily unless we check attendIds
          },
        ];
      }
    }
  }

  @override
  void dispose() {
    _locationController.dispose();
    _titleController.dispose();
    _descriptionController.dispose();
    _contactNameController.dispose();
    _contactEmailController.dispose();
    _contactPhoneController.dispose();
    _contactLineIdController.dispose();
    super.dispose();
  }

  Future<void> _selectDateTime(BuildContext context) async {
    final now = DateTime.now();
    // Ensure firstDate includes startTime if it's in the past (for editing)
    final firstDate = startTime.isBefore(now) ? startTime : now;
    
    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: startTime,
      firstDate: firstDate, // Restrict to now or current startTime if editing past event
      lastDate: DateTime(2101),
    );
    if (pickedDate != null) {
      final TimeOfDay? pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(startTime),
      );
      if (pickedTime != null) {
        final newDateTime = DateTime(
          pickedDate.year,
          pickedDate.month,
          pickedDate.day,
          pickedTime.hour,
          pickedTime.minute,
        );

        if (newDateTime.isBefore(DateTime.now())) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(AppLocalizations.of(context)!.pleaseEnterFutureTime ?? '請選擇未來的時間'),
              backgroundColor: Colors.red,
            ),
          );
          return;
        }

        setState(() {
          startTime = newDateTime;
        });
      }
    }
  }

  Future<void> _selectEndTime(BuildContext context) async {
    final initialDate = endTime ?? startTime.add(Duration(hours: 1));
    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: startTime, // End time must be after start time
      lastDate: DateTime(2101),
    );
    if (pickedDate != null) {
      final TimeOfDay? pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(initialDate),
      );
      if (pickedTime != null) {
        final newDateTime = DateTime(
          pickedDate.year,
          pickedDate.month,
          pickedDate.day,
          pickedTime.hour,
          pickedTime.minute,
        );

        if (newDateTime.isBefore(startTime)) {
           ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(AppLocalizations.of(context)!.endTimeMustBeAfterStartTime ?? '結束時間必須晚於開始時間'),
              backgroundColor: Colors.red,
            ),
          );
          return;
        }

        setState(() {
          endTime = newDateTime;
        });
      }
    }
  }

  void _updateWidget(String title, String time) async {
    try {
      await HomeWidget.setAppGroupId('group.com.example.scheduleManagement');
      await HomeWidget.saveWidgetData<String>('title', title);
      await HomeWidget.saveWidgetData<String>('content', '時間: $time');
      await HomeWidget.updateWidget(
        iOSName: 'ScheduleWidget',
        androidName: 'ScheduleWidgetProvider',
      );
    } catch (e) {
      debugPrint('Error updating widget: $e');
    }
  }

  void _pickLocation() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) =>
            LocationPickerScreen(initialLat: latitude, initialLon: longitude),
      ),
    );

    if (result != null && result is Map) {
      final lat = result['latitude'] as double;
      final lon = result['longitude'] as double;
      final pickedName = result['name'] as String?;

      setState(() {
        latitude = lat;
        longitude = lon;
        _locationController.text = pickedName ?? "Loading...";
      });

      try {
        // 1. Get Address
        final addressFuture = apiService.reverseGeocode(lat, lon);
        
        // 2. Get Nearby POIs
        final poisFuture = apiService.getNearbyPlaces(lat, lon);

        final results = await Future.wait([
            addressFuture,
            poisFuture.catchError((e) => <Map<String, dynamic>>[])
        ]);
        
        final address = results[0] as String;
        final pois = results[1] as List<Map<String, dynamic>>;

        if (!mounted) return;

        // Show selection sheet
        showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          shape: RoundedRectangleBorder(
             borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
          ),
          builder: (context) {
             return DraggableScrollableSheet(
               initialChildSize: 0.5,
               minChildSize: 0.3,
               maxChildSize: 0.9,
               expand: false,
               builder: (context, scrollController) {
                 return Column(
                   children: [
                     Padding(
                       padding: const EdgeInsets.all(16.0),
                       child: Text(
                         'Select Location',
                         style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                       ),
                     ),
                     Expanded(
                       child: ListView(
                         controller: scrollController,
                         children: [
                            // Option 0: Selected POI (if available)
                            if (pickedName != null) ...[
                               ListTile(
                                 leading: Icon(Icons.star, color: Colors.orange),
                                 title: Text(pickedName),
                                 subtitle: Text('Selected on Map'),
                                 onTap: () {
                                   Navigator.pop(context, pickedName);
                                 },
                               ),
                               Divider(),
                            ],

                            // Option 1: The precise address
                            ListTile(
                              leading: Icon(Icons.location_on, color: Colors.red),
                              title: Text(address),
                              subtitle: Text('Precise Address'),
                              onTap: () {
                                Navigator.pop(context, address);
                              },
                            ),
                            Divider(),
                            if (pois.isEmpty)
                               Padding(
                                 padding: const EdgeInsets.all(16.0),
                                 child: Text('No nearby places found', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
                               ),
                            // Option 2...N: POIs
                            ...pois.map((poi) {
                               IconData icon = Icons.place;
                               String category = poi['category'] ?? 'Unknown';
                               if (category == 'amenity' || category == 'restaurant' || category == 'cafe') icon = Icons.restaurant;
                               else if (category.contains('shop')) icon = Icons.shopping_bag;
                               else if (category.contains('transport')) icon = Icons.train;
                               
                               return ListTile(
                                 leading: Icon(icon, color: Colors.blue),
                                 title: Text(poi['name'] ?? 'Unknown Place'),
                                 subtitle: Text('${poi['category']} • ${poi['distance']}m'),
                                 onTap: () {
                                   Navigator.pop(context, poi['name']);
                                 },
                               );
                            }).toList(),
                         ],
                       ),
                     ),
                   ],
                 );
               }
             );
          }
        ).then((selectedName) {
           if (selectedName != null && selectedName is String) {
              setState(() {
                 _locationController.text = selectedName;
              });
           } else {
              // If dismissed without selection:
              // - If we had a pickedName, _locationController.text is already pickedName.
              // - If we didn't, it was "Loading...". We should fallback to address.
              if (_locationController.text == "Loading...") {
                  setState(() {
                      _locationController.text = address;
                  });
              }
           }
        });

      } catch (e) {
        if (mounted) {
          setState(() {
            _locationController.text =
                "Pinned Location (${latitude!.toStringAsFixed(4)}, ${longitude!.toStringAsFixed(4)})";
          });
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('Failed to get location info: $e')));
        }
      }
    }
  }

  void _showAttendeeSelector() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => AttendeeSelector(
        initialSelectedContacts: selectedContacts,
        onSelectionChanged: (contacts) {
          setState(() {
            selectedContacts = contacts.cast<Map<String, dynamic>>();
          });
        },
      ),
    );
  }

  void _save() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      location = _locationController.text;

      // Prepare contact info from first attend if available, for backward compat
      String? contactName;
      String? contactEmail;
      String? contactPhone;
      String? contactLineId;

      if (selectedContacts.isNotEmpty) {
        final first = selectedContacts.first;
        contactName = first['name'] ?? first['nick_name'] ?? first['user_id'];
        contactEmail = first['email'];
        contactPhone = first['phone'];
        contactLineId = first['line_id'];
      }

      try {
        if (widget.schedule == null) {
          // Create
          final newSchedule = await apiService.createSchedule(
            Schedule(
              id: '',
              title: _titleController.text,
              description: _descriptionController.text,
              startTime: startTime,
              endTime: endTime,
              location: location,
              latitude: latitude,
              longitude: longitude,
              status: ScheduleStatus.pending, // Use constant
              transportMode: transportMode,
              attends: selectedContacts.map((c) {
                return {
                  'user_id': c['contact_user_id'] ?? c['user_id'],
                  'contact_id': c['id'],
                  'name': c['nick_name'] ?? c['name'] ?? c['full_name'],
                  'email': c['email'],
                  'phone': c['phone'],
                  'line_id': c['line_id'],
                  'status': 'P',
                };
              }).toList(),
              attendIds: selectedContacts
                  .where((c) => c['id'] != null)
                  .map((c) => c['id'].toString())
                  .toList(),
              contactName: contactName,
              contactEmail: contactEmail,
              contactPhone: contactPhone,
              contactLineId: contactLineId,
            ),
          );
          _updateWidget(
            _titleController.text,
            DateFormat('HH:mm').format(startTime),
          );
          Navigator.pop(context, newSchedule);
        } else {
          // Update
          final scheduleData = {
            'title': _titleController.text,
            'description': _descriptionController.text,
            'start_time': startTime.toIso8601String(),
            'end_time': endTime?.toIso8601String(),
            'location': _locationController.text,
            'transport_mode': transportMode,
            'latitude': latitude,
            'longitude': longitude,
            'attends': selectedContacts.map((c) {
              return {
                'user_id': c['contact_user_id'] ?? c['user_id'],
                'contact_id': c['id'],
                'name': c['nick_name'] ?? c['name'] ?? c['full_name'],
                'email': c['email'],
                'phone': c['phone'],
                'line_id': c['line_id'],
                'status': c['status'] ?? 'P',
              };
            }).toList(),
            'contact_name': contactName,
            'contact_email': contactEmail,
            'contact_phone': contactPhone,
            'contact_line_id': contactLineId,
          };
          final updatedSchedule = await apiService.updateSchedule(
            widget.schedule!.id,
            scheduleData,
          );
          print(
            'DEBUG: AddScheduleScreen popping with updated schedule: ${updatedSchedule.latitude}, ${updatedSchedule.longitude}',
          );
          _updateWidget(
            _titleController.text,
            DateFormat('HH:mm').format(startTime),
          );
          Navigator.pop(context, updatedSchedule);
        }
      } catch (e) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to save schedule: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.schedule == null
              ? AppLocalizations.of(context)!.addSchedule
              : 'Edit Schedule',
        ),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextFormField(
                controller: _titleController,
                decoration: InputDecoration(
                  labelText: AppLocalizations.of(context)!.title,
                  border: OutlineInputBorder(),
                ),
                autovalidateMode: AutovalidateMode
                    .onUserInteraction, // Fix validation behavior
                validator: (value) => value!.isEmpty
                    ? AppLocalizations.of(context)!.pleaseEnterTitle
                    : null,
              ),
              SizedBox(height: 16),
              TextFormField(
                controller: _descriptionController,
                decoration: InputDecoration(
                  labelText: AppLocalizations.of(context)!.description,
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
              ),
              SizedBox(height: 16),
              ListTile(
                title: Text(AppLocalizations.of(context)!.startTime),
                subtitle: Text(
                  DateFormat('yyyy-MM-dd HH:mm').format(startTime),
                ),
                trailing: Icon(Icons.calendar_today),
                onTap: () => _selectDateTime(context),
                shape: RoundedRectangleBorder(
                  side: BorderSide(color: Colors.grey),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              SizedBox(height: 16),
              ListTile(
                title: Text(AppLocalizations.of(context)!.endTime ?? 'End Time'),
                subtitle: Text(
                  endTime != null
                      ? DateFormat('yyyy-MM-dd HH:mm').format(endTime!)
                      : AppLocalizations.of(context)!.notSet ?? 'Not Set',
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (endTime != null)
                      IconButton(
                        icon: Icon(Icons.clear),
                        onPressed: () => setState(() => endTime = null),
                      ),
                    Icon(Icons.calendar_today),
                  ],
                ),
                onTap: () => _selectEndTime(context),
                shape: RoundedRectangleBorder(
                  side: BorderSide(color: Colors.grey),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: transportMode,
                decoration: InputDecoration(
                  labelText: AppLocalizations.of(context)!.transportMode,
                  border: OutlineInputBorder(),
                ),
                items: transportModes.map((mode) {
                  return DropdownMenuItem(
                    value: mode['value'],
                    child: Text(mode['label']!),
                  );
                }).toList(),
                onChanged: (value) => setState(() => transportMode = value!),
              ),
              SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _locationController,
                      decoration: InputDecoration(
                        labelText: AppLocalizations.of(context)!.location,
                        border: OutlineInputBorder(),
                      ),
                      onSaved: (value) => location = value,
                    ),
                  ),
                  SizedBox(width: 8),
                  IconButton(
                    icon: Icon(
                      Icons.map,
                      color: latitude != null ? Colors.blue : Colors.grey,
                    ),
                    onPressed: _pickLocation,
                    tooltip: 'Select on Map',
                  ),
                ],
              ),
              if (latitude != null)
                Padding(
                  padding: const EdgeInsets.only(top: 4.0),
                  child: Text(
                    '📍 Coordinate selected',
                    style: TextStyle(color: Colors.blue, fontSize: 12),
                  ),
                ),
              SizedBox(height: 24),
              // Participants Section
              Text(
                '${AppLocalizations.of(context)!.participants} (${selectedContacts.length})',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ...selectedContacts.map((contact) {
                    final name =
                        contact['nick_name'] ?? // Prioritize nick_name for friends
                        contact['name'] ??
                        contact['full_name'] ??
                        contact['contact_user_id'] ?? // Fallback to contact_user_id
                        'Unknown';

                    return Chip(
                      avatar: CircleAvatar(
                        backgroundImage: contact['profile_picture'] != null
                            ? NetworkImage(contact['profile_picture'])
                            : null,
                        child: contact['profile_picture'] == null
                            ? Text(
                                name.isNotEmpty ? name[0].toUpperCase() : '?',
                              )
                            : null,
                      ),
                      label: Text(name),
                      onDeleted: () {
                        setState(() {
                          selectedContacts.remove(contact);
                        });
                      },
                    );
                  }).toList(),
                  ActionChip(
                    avatar: Icon(Icons.person_add),
                    label: Text('選擇參與者'),
                    onPressed: _showAttendeeSelector,
                  ),
                ],
              ),

              SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _save,
                  child: Text(
                    AppLocalizations.of(context)!.saveSchedule,
                    style: TextStyle(fontSize: 18),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
