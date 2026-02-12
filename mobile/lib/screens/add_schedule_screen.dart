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
    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: startTime,
      firstDate: DateTime(2000),
      lastDate: DateTime(2101),
    );
    if (pickedDate != null) {
      final TimeOfDay? pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(startTime),
      );
      if (pickedTime != null) {
        setState(() {
          startTime = DateTime(
            pickedDate.year,
            pickedDate.month,
            pickedDate.day,
            pickedTime.hour,
            pickedTime.minute,
          );
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
      setState(() {
        latitude = result['latitude'];
        longitude = result['longitude'];
        // If location text is empty, maybe set a placeholder?
        if (_locationController.text.isEmpty) {
          _locationController.text = "Pinned Location";
        }
      });
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
        contactName = first['name'] ?? first['full_name'] ?? first['user_id'];
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
              location: location,
              latitude: latitude,
              longitude: longitude,
              status: ScheduleStatus.pending, // Use constant
              transportMode: transportMode,
              attends: selectedContacts, // Send full list including guests
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
            'location': _locationController.text,
            'transport_mode': transportMode,
            'latitude': latitude,
            'longitude': longitude,
            'attends': selectedContacts
                .map(
                  (c) => {
                    'contact_id': c['id'], // Ensure contact_id is sent
                    'contact_user_id':
                        c['contact_user_id'], // Keep for backward compatibility or linking
                    'nick_name': c['nick_name'] ?? c['name'],
                    'name': c['name'] ?? c['nick_name'], // Fallback
                    'email': c['email'],
                    'phone': c['phone'],
                    'line_id': c['line_id'],
                  },
                )
                .toList(),
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
