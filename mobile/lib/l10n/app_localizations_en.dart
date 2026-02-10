// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Schedule Management';

  @override
  String get settings => 'Settings';

  @override
  String get profile => 'Profile';

  @override
  String get language => 'Language';

  @override
  String get logout => 'Logout';

  @override
  String get login => 'Login';

  @override
  String get cancel => 'Cancel';

  @override
  String get save => 'Save';

  @override
  String get edit => 'Edit';

  @override
  String get delete => 'Delete';

  @override
  String get confirm => 'Confirm';

  @override
  String get name => 'Name';

  @override
  String get phone => 'Phone';

  @override
  String get email => 'Email';

  @override
  String get lineId => 'Line ID';

  @override
  String get accountNumber => 'Account Number';

  @override
  String get schedules => 'Schedules';

  @override
  String get calendar => 'Calendar';

  @override
  String get callLog => 'Call Log';

  @override
  String get map => 'Map';

  @override
  String get aiChat => 'AI Chat';

  @override
  String get aiChatHint => 'Try: \"Meeting at Taipei 101 tomorrow 3pm\"';

  @override
  String get mySchedules => 'My Schedules';

  @override
  String get noSchedules => 'No schedules found';

  @override
  String get loading => 'Loading...';

  @override
  String get error => 'Error';

  @override
  String get success => 'Success';

  @override
  String get profileUpdated => 'Profile updated successfully';

  @override
  String get photoUploaded => 'Photo uploaded successfully';

  @override
  String get addSchedule => 'Add Schedule';

  @override
  String get title => 'Title';

  @override
  String get description => 'Description';

  @override
  String get startTime => 'Start Time';

  @override
  String get transportMode => 'Transport Mode';

  @override
  String get location => 'Location';

  @override
  String get saveSchedule => 'Save Schedule';

  @override
  String get inviteFriends => 'Invite Friends';

  @override
  String invited(Object count) {
    return 'Invited $count people';
  }

  @override
  String get pleaseEnterTitle => 'Please enter title';

  @override
  String get myContacts => 'My Contacts';

  @override
  String get sessionExpired => 'Session expired. Redirecting to login...';

  @override
  String get user => 'User';

  @override
  String get month => 'Month';

  @override
  String get week => 'Week';

  @override
  String get day => 'Day';

  @override
  String get noEvents => 'No events';

  @override
  String eventsCount(Object count) {
    return '$count events';
  }

  @override
  String get statusActive => 'Active';

  @override
  String get statusPending => 'Pending';

  @override
  String get statusNotGoing => 'Not Going';

  @override
  String get statusCancelled => 'Cancelled';

  @override
  String get iosLimitation => 'iOS Limitation';

  @override
  String get iosLimitationDesc =>
      'Call logs are not accessible due to iOS privacy restrictions.';

  @override
  String get androidOnly => 'This feature is only available on Android.';

  @override
  String get permissionRequired => 'Permission Required';

  @override
  String get permissionDesc =>
      'Call log permission is required to display history.';

  @override
  String get openSettings => 'Open Settings';

  @override
  String get noCallLogs => 'No call logs';

  @override
  String get incoming => 'Incoming';

  @override
  String get outgoing => 'Outgoing';

  @override
  String get missed => 'Missed';

  @override
  String get rejected => 'Rejected';

  @override
  String get unknown => 'Unknown';

  @override
  String get unknownNumber => 'Unknown Number';

  @override
  String get today => 'Today';

  @override
  String get yesterday => 'Yesterday';

  @override
  String get hours => 'hrs';

  @override
  String get minutes => 'mins';

  @override
  String get seconds => 'secs';

  @override
  String get notConnected => 'Not connected';
}
