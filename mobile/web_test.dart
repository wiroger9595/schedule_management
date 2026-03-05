import 'dart:io';

void main() {
  bool kIsWeb = true;
  var x = kIsWeb ? 'web' : (Platform.isIOS ? 'ios' : 'android');
  print(x);
}
