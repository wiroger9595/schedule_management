import 'package:easy_localization/easy_localization.dart';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';
import '../utils/constants.dart'; // Import constants
import 'package:home_widget/home_widget.dart';
import '../widgets/contact_picker.dart';
import '../widgets/attendee_selector.dart';
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
  String? transportMode = 'walk';
  double? latitude;
  double? longitude;
  bool _isOnline = false;
  bool _isLoadingLocation = false;
  bool _isSearchingLocation = false;
  List<Map<String, dynamic>> _locationSearchResults = [];
  Timer? _debounceTimer;

  final TextEditingController _locationController = TextEditingController();
  final TextEditingController _onlineLinkController = TextEditingController();
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _contactNameController = TextEditingController();
  final TextEditingController _contactEmailController = TextEditingController();
  final TextEditingController _contactPhoneController = TextEditingController();
  final TextEditingController _contactLineIdController =
      TextEditingController();

  List<Map<String, String>> get transportModes => [
    {'value': 'car', 'label': 'car'.tr()},
    {'value': 'motorcycle', 'label': 'motorcycle'.tr()},
    {'value': 'transit', 'label': 'transit'.tr()},
    {'value': 'bike', 'label': 'bicycle'.tr()},
    {'value': 'walk', 'label': 'walkMode'.tr()},
  ];

  /// Returns true when the selected location is outside Taiwan's bounding box.
  bool get _isInternational {
    if (latitude == null || longitude == null) return false;
    const double latMin = 21.5, latMax = 25.5;
    const double lonMin = 119.5, lonMax = 122.5;
    return latitude! < latMin || latitude! > latMax ||
           longitude! < lonMin || longitude! > lonMax;
  }

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
      _isOnline = s.isOnline == true;
      _locationController.text = location ?? '';
      if (s.isOnline == true) _onlineLinkController.text = location ?? '';
      _titleController.text = s.title;
      _descriptionController.text = s.description ?? '';
      _contactNameController.text = s.contactName ?? '';
      _contactEmailController.text = s.contactEmail ?? '';
      _contactPhoneController.text = s.contactPhone ?? '';
      _contactLineIdController.text = s.contactLineId ?? '';

      if (s.attends != null) {
        selectedContacts = s.attends!.map((att) {
          final mapped = Map<String, dynamic>.from(att);
          mapped['attend_id'] = mapped['id']; // preserve attend primary key
          mapped['id'] = mapped['contact_id']; // frontend UI relies on 'id' being the contact_id
          return mapped;
        }).toList();
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
    _debounceTimer?.cancel();
    _locationController.dispose();
    _onlineLinkController.dispose();
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
              content: Text('pleaseEnterFutureTime'.tr() ?? '請選擇未來的時間'),
              backgroundColor: Colors.red,
            ),
          );
          return;
        }

        setState(() {
          startTime = newDateTime;
          // 自動將 endTime 調整為 startTime 之後，避免 end time 在 start time 之前
          if (endTime != null && endTime!.isBefore(startTime)) {
            endTime = startTime.add(Duration(hours: 1));
          }
        });
      }
    }
  }

  Future<void> _selectEndTime(BuildContext context) async {
    DateTime initialDate = endTime ?? startTime.add(Duration(hours: 1));
    
    // 確保 initialDate 不會早於 firstDate (startTime)，避免 Flutter DatePicker 拋出 Assertion Error (crash)
    if (initialDate.isBefore(startTime)) {
      initialDate = startTime.add(Duration(hours: 1));
    }

    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime(startTime.year, startTime.month, startTime.day), // 以天為單位，確保不會被時間差異影響 assertion
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
              content: Text('endTimeMustBeAfterStartTime'.tr() ?? '結束時間必須晚於開始時間'),
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
      await HomeWidget.setAppGroupId('group.com.schedulo.app');
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
      final pickedName = result['name'] as String? ?? result['address'] as String?;

      if (pickedName != null && pickedName.isNotEmpty && pickedName != 'Selected Location') {
        setState(() {
          latitude = lat;
          longitude = lon;
          _locationController.text = pickedName;
          if (_isInternational) transportMode = null;
        });
      } else {
        setState(() {
          latitude = lat;
          longitude = lon;
          _isLoadingLocation = true;
          _locationController.text = "解析地址中...";
        });

        try {
          final address = await apiService.reverseGeocode(lat, lon);
          if (mounted) {
             setState(() {
                _locationController.text = address;
                _isLoadingLocation = false;
             });
          }
        } catch (e) {
          if (mounted) {
            setState(() {
              _isLoadingLocation = false;
              _locationController.text =
                  "已選擇座標 (${latitude!.toStringAsFixed(4)}, ${longitude!.toStringAsFixed(4)})";
            });
          }
        }
      }
    }
  }

  void _selectSearchResult(Map<String, dynamic> place) {
    setState(() {
      _locationController.text = place['name'] ?? '';
      latitude = (place['lat'] ?? place['latitude']) as double?;
      longitude = (place['lon'] ?? place['longitude']) as double?;
      _locationSearchResults.clear();
      FocusScope.of(context).unfocus();
      // Reset transport mode when switching to an international location
      if (_isInternational) transportMode = null;
    });
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
      location = _isOnline ? _onlineLinkController.text.trim() : _locationController.text;

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
              latitude: _isOnline ? null : latitude,
              longitude: _isOnline ? null : longitude,
              isOnline: _isOnline,
              status: ScheduleStatus.pending, // Use constant
              transportMode: transportMode ?? 'walk',
              attends: selectedContacts.map((c) {
                return {
                  'user_id': c['contact_user_id'], // Only invited user's id; null if unlinked
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
            'location': location,
            'transport_mode': transportMode,
            'is_online': _isOnline,
            'latitude': _isOnline ? null : latitude,
            'longitude': _isOnline ? null : longitude,
            'attends': selectedContacts.map((c) {
              return {
                'user_id': c['contact_user_id'], // Only invited user's id; null if unlinked
                'contact_id': c['id'] ?? c['contact_id'], // 'id' is now the contact_id due to normalization
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
          debugPrint(
            'AddScheduleScreen popping with updated schedule: ${updatedSchedule.latitude}, ${updatedSchedule.longitude}',
          );
          _updateWidget(
            _titleController.text,
            DateFormat('HH:mm').format(startTime),
          );
          Navigator.pop(context, updatedSchedule);
        }
      } catch (e) {
        String errorMsg = e.toString();
        // Remove "Exception: " prefix if present from dart exceptions
        if (errorMsg.startsWith('Exception: ')) {
          errorMsg = errorMsg.substring(11);
        }
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(
          content: Text(errorMsg),
          backgroundColor: Colors.red,
        ));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.schedule == null
              ? 'addSchedule'.tr()
              : 'editSchedule'.tr(),
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
                  labelText: 'title'.tr(),
                  border: OutlineInputBorder(),
                ),
                autovalidateMode: AutovalidateMode
                    .onUserInteraction, // Fix validation behavior
                validator: (value) => value!.isEmpty
                    ? 'pleaseEnterTitle'.tr()
                    : null,
              ),
              SizedBox(height: 16),
              TextFormField(
                controller: _descriptionController,
                decoration: InputDecoration(
                  labelText: 'description'.tr(),
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
              ),
              SizedBox(height: 16),
              ListTile(
                title: Text('startTime'.tr()),
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
                title: Text('endTime'.tr() ?? 'End Time'),
                subtitle: Text(
                  endTime != null
                      ? DateFormat('yyyy-MM-dd HH:mm').format(endTime!)
                      : 'notSet'.tr() ?? 'Not Set',
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
              if (!_isInternational) ...[
                DropdownButtonFormField<String>(
                  value: transportMode,
                  decoration: InputDecoration(
                    labelText: 'transportMode'.tr(),
                    border: OutlineInputBorder(),
                  ),
                  items: transportModes.map((mode) {
                    return DropdownMenuItem(
                      value: mode['value'],
                      child: Text(mode['label']!),
                    );
                  }).toList(),
                  onChanged: (value) => setState(() => transportMode = value),
                ),
                SizedBox(height: 16),
              ],
              // Online / Physical toggle
              Row(
                children: [
                  Expanded(
                    child: SegmentedButton<bool>(
                      segments: [
                        ButtonSegment(
                          value: false,
                          label: Text('physicalLocation'.tr()),
                          icon: Icon(Icons.location_on),
                        ),
                        ButtonSegment(
                          value: true,
                          label: Text('onlineEvent'.tr()),
                          icon: Icon(Icons.video_call),
                        ),
                      ],
                      selected: {_isOnline},
                      onSelectionChanged: (sel) => setState(() {
                        _isOnline = sel.first;
                        // clear the other field when switching
                        if (_isOnline) {
                          latitude = null;
                          longitude = null;
                          _locationController.clear();
                        } else {
                          _onlineLinkController.clear();
                        }
                      }),
                    ),
                  ),
                ],
              ),
              SizedBox(height: 12),
              if (_isOnline) ...[
                TextFormField(
                  controller: _onlineLinkController,
                  decoration: InputDecoration(
                    labelText: 'onlineMeetingLink'.tr(),
                    hintText: 'onlineMeetingLinkHint'.tr(),
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.link),
                  ),
                  keyboardType: TextInputType.url,
                ),
              ] else ...[
                Row(
                  children: [
                    Expanded(
                      child: InkWell(
                        onTap: _pickLocation,
                        child: AbsorbPointer(
                          child: TextFormField(
                            controller: _locationController,
                            readOnly: true,
                            decoration: InputDecoration(
                              labelText: 'location'.tr(),
                              border: OutlineInputBorder(),
                              hintText: 'tapToSelectOnMap'.tr(),
                              suffixIcon: (_isLoadingLocation || _isSearchingLocation)
                                  ? Container(
                                      width: 24,
                                      height: 24,
                                      padding: EdgeInsets.all(12),
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.grey,
                                      ),
                                    )
                                  : null,
                            ),
                            onSaved: (value) => location = value,
                          ),
                        ),
                      ),
                    ),
                    SizedBox(width: 8),
                    IconButton(
                      icon: Icon(
                        Icons.map,
                        color: latitude != null ? Colors.black : Colors.grey,
                      ),
                      onPressed: _isLoadingLocation ? null : _pickLocation,
                      tooltip: 'Select on Map',
                    ),
                  ],
                ),
                if (latitude != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4.0),
                    child: Text(
                      'coordinateSelected'.tr(),
                      style: TextStyle(color: Colors.black87, fontSize: 12),
                    ),
                  ),
              ],
              // Search results list removed, search happens in the map now.
              SizedBox(height: 24),
              // Participants Section
              Text(
                '${'participants'.tr()} (${selectedContacts.length})',
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
                    label: Text('selectParticipants'.tr()),
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
                    'saveSchedule'.tr(),
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
