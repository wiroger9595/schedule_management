import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';
import 'package:home_widget/home_widget.dart';
import '../widgets/contact_picker.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

class AddScheduleScreen extends StatefulWidget {
  @override
  _AddScheduleScreenState createState() => _AddScheduleScreenState();
}

class _AddScheduleScreenState extends State<AddScheduleScreen> {
  final _formKey = GlobalKey<FormState>();
  final ApiService apiService = ApiService();
  
  List<Map<String, dynamic>> selectedContacts = [];
  
  String title = '';
  String? description;
  DateTime startTime = DateTime.now().add(Duration(hours: 1));
  String? location;
  String transportMode = 'car';

  final List<Map<String, String>> transportModes = [
    {'value': 'car', 'label': '汽車'},
    {'value': 'motorcycle', 'label': '機車'},
    {'value': 'transit', 'label': '大眾運輸 (TDX)'},
    {'value': 'bike', 'label': '腳踏車'},
    {'value': 'walk', 'label': '行走'},
  ];

  Future<void> _selectDateTime(BuildContext context) async {
    final DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: startTime,
      firstDate: DateTime.now(),
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

  void _updateWidget(String title, String time) {
    HomeWidget.saveWidgetData<String>('title', title);
    HomeWidget.saveWidgetData<String>('content', '時間: $time');
    HomeWidget.updateWidget(
      iOSName: 'ScheduleWidget',
      androidName: 'ScheduleWidgetProvider',
    );
  }

  void _save() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      try {
        await apiService.createSchedule(Schedule(
          id: '',
          title: title,
          description: description,
          startTime: startTime,
          location: location,
          status: 'PENDING',
          transportMode: transportMode,
          attendeeIds: selectedContacts.map((c) => c['id'] as String).toList(),
        ));
        
        _updateWidget(title, DateFormat('HH:mm').format(startTime));
        
        Navigator.pop(context);
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save schedule')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(AppLocalizations.of(context)!.addSchedule)),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextFormField(
                decoration: InputDecoration(labelText: AppLocalizations.of(context)!.title, border: OutlineInputBorder()),
                validator: (value) => value!.isEmpty ? AppLocalizations.of(context)!.pleaseEnterTitle : null,
                onSaved: (value) => title = value!,
              ),
              SizedBox(height: 16),
              TextFormField(
                decoration: InputDecoration(labelText: AppLocalizations.of(context)!.description, border: OutlineInputBorder()),
                maxLines: 3,
                onSaved: (value) => description = value,
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
              TextFormField(
                decoration: InputDecoration(labelText: AppLocalizations.of(context)!.location, border: OutlineInputBorder()),
                onSaved: (value) => location = value,
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
              SizedBox(height: 16),
              OutlinedButton.icon(
                icon: Icon(Icons.people),
                label: Text(selectedContacts.isEmpty 
                    ? AppLocalizations.of(context)!.inviteFriends
                    : AppLocalizations.of(context)!.invited(selectedContacts.length)),
                onPressed: () {
                  showModalBottomSheet(
                    context: context,
                    isScrollControlled: true,
                    builder: (context) => ContactPicker(
                      initialSelectedIds: selectedContacts.map((c) => c['id'] as String).toList(),
                      onSelectionChanged: (selected) {
                        setState(() {
                          selectedContacts = selected;
                        });
                      },
                    ),
                  );
                },
                style: OutlinedButton.styleFrom(
                  minimumSize: Size(double.infinity, 50),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
