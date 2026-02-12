import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';
import 'package:home_widget/home_widget.dart';
import '../widgets/contact_picker.dart';
import '../l10n/app_localizations.dart';
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
  final TextEditingController _contactLineIdController = TextEditingController();

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
        builder: (context) => LocationPickerScreen(
          initialLat: latitude, 
          initialLon: longitude
        ),
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

  void _save() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      location = _locationController.text;
      
      try {
        if (widget.schedule == null) {
          // Create
          final newSchedule = await apiService.createSchedule(Schedule(
            id: '',
            title: _titleController.text,
            description: _descriptionController.text,
            startTime: startTime,
            location: location,
            latitude: latitude,
            longitude: longitude,
            status: 'PENDING',
            transportMode: transportMode,
            attendeeIds: selectedContacts.map((c) => c['id'] as String).toList(),
            contactName: _contactNameController.text,
            contactEmail: _contactEmailController.text,
            contactPhone: _contactPhoneController.text,
            contactLineId: _contactLineIdController.text,
          ));
          _updateWidget(_titleController.text, DateFormat('HH:mm').format(startTime));
          Navigator.pop(context, newSchedule);
        } else {
          // Update
          final updatedSchedule = await apiService.updateSchedule(widget.schedule!.id, {
            'title': _titleController.text,
            'description': _descriptionController.text,
            'start_time': startTime.toIso8601String(),
            'location': location,
            'transport_mode': transportMode,
            'latitude': latitude,
            'longitude': longitude,
            'contact_name': _contactNameController.text,
            'contact_email': _contactEmailController.text,
            'contact_phone': _contactPhoneController.text,
            'contact_line_id': _contactLineIdController.text,
          });
          print('DEBUG: AddScheduleScreen popping with updated schedule: ${updatedSchedule.latitude}, ${updatedSchedule.longitude}');
          _updateWidget(_titleController.text, DateFormat('HH:mm').format(startTime));
          Navigator.pop(context, updatedSchedule);
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save schedule: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.schedule == null ? AppLocalizations.of(context)!.addSchedule : 'Edit Schedule')),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextFormField(
                controller: _titleController,
                decoration: InputDecoration(labelText: AppLocalizations.of(context)!.title, border: OutlineInputBorder()),
                validator: (value) => value!.isEmpty ? AppLocalizations.of(context)!.pleaseEnterTitle : null,
              ),
              SizedBox(height: 16),
              TextFormField(
                controller: _descriptionController,
                decoration: InputDecoration(labelText: AppLocalizations.of(context)!.description, border: OutlineInputBorder()),
                maxLines: 3,
              ),
              SizedBox(height: 16),
              ListTile(
                title: Text(AppLocalizations.of(context)!.startTime),
                subtitle: Text(DateFormat('yyyy-MM-dd HH:mm').format(startTime)),
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
                decoration: InputDecoration(labelText: AppLocalizations.of(context)!.transportMode, border: OutlineInputBorder()),
                items: transportModes.map((mode) {
                  return DropdownMenuItem(value: mode['value'], child: Text(mode['label']!));
                }).toList(),
                onChanged: (value) => setState(() => transportMode = value!),
              ),
              SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _locationController,
                      decoration: InputDecoration(labelText: AppLocalizations.of(context)!.location, border: OutlineInputBorder()),
                      onSaved: (value) => location = value,
                    ),
                  ),
                  SizedBox(width: 8),
                  IconButton(
                    icon: Icon(Icons.map, color: latitude != null ? Colors.blue : Colors.grey),
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
                    style: TextStyle(color: Colors.blue, fontSize: 12)
                  ),
                ),
              SizedBox(height: 24),
              Text('Attendee Details', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _contactNameController,
                      decoration: InputDecoration(labelText: 'Name', border: OutlineInputBorder()),
                    ),
                  ),
                  SizedBox(width: 8),
                  IconButton(
                    icon: Icon(Icons.person_search, color: Colors.blue),
                    onPressed: () {
                      showModalBottomSheet(
                        context: context,
                        isScrollControlled: true,
                        builder: (context) => ContactPicker(
                          initialSelectedIds: selectedContacts.map((c) => c['id'] as String).toList(),
                          onSelectionChanged: (selected) {
                            setState(() {
                              selectedContacts = selected;
                              if (selected.isNotEmpty) {
                                final c = selected.first;
                                // Use neck_name or full_name or name
                                _contactNameController.text = c['neck_name'] ?? c['full_name'] ?? c['name'] ?? '';
                                _contactEmailController.text = c['email'] ?? '';
                                _contactPhoneController.text = c['phone'] ?? '';
                                _contactLineIdController.text = c['line_id'] ?? '';
                              }
                            });
                          },
                        ),
                      );
                    },
                    tooltip: 'Select Contact',
                  ),
                ],
              ),
              SizedBox(height: 12),
              TextFormField(
                controller: _contactEmailController,
                decoration: InputDecoration(labelText: 'Email', border: OutlineInputBorder()),
                keyboardType: TextInputType.emailAddress,
              ),
              SizedBox(height: 12),
              TextFormField(
                controller: _contactPhoneController,
                decoration: InputDecoration(labelText: 'Phone', border: OutlineInputBorder()),
                keyboardType: TextInputType.phone,
              ),
              SizedBox(height: 12),
              TextFormField(
                controller: _contactLineIdController,
                decoration: InputDecoration(labelText: 'Line ID', border: OutlineInputBorder()),
              ),

              SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _save,
                  child: Text(AppLocalizations.of(context)!.saveSchedule, style: TextStyle(fontSize: 18)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
