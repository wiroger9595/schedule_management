// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appTitle => '行程管理';

  @override
  String get settings => '設定';

  @override
  String get profile => '個人資料';

  @override
  String get language => '語言';

  @override
  String get logout => '登出';

  @override
  String get login => '登入';

  @override
  String get cancel => '取消';

  @override
  String get save => '儲存';

  @override
  String get edit => '編輯';

  @override
  String get delete => '刪除';

  @override
  String get confirm => '確認';

  @override
  String get name => '姓名';

  @override
  String get phone => '電話';

  @override
  String get email => '電子郵件';

  @override
  String get lineId => 'Line ID';

  @override
  String get accountNumber => '帳號';

  @override
  String get schedules => '行程列表';

  @override
  String get calendar => '行事曆';

  @override
  String get callLog => '通話記錄';

  @override
  String get map => '地圖';

  @override
  String get aiChat => 'AI 助手';

  @override
  String get aiChatHint => '試試看：「明天下午3點去台北101開會」';

  @override
  String get mySchedules => '我的行程';

  @override
  String get noSchedules => '目前沒有行程';

  @override
  String get loading => '載入中...';

  @override
  String get error => '錯誤';

  @override
  String get success => '成功';

  @override
  String get profileUpdated => '個人資料更新成功';

  @override
  String get photoUploaded => '頭像上傳成功';

  @override
  String get addSchedule => '新增行程';

  @override
  String get title => '標題';

  @override
  String get description => '描述';

  @override
  String get startTime => '開始時間';

  @override
  String get transportMode => '交通工具';

  @override
  String get location => '地點';

  @override
  String get saveSchedule => '儲存行程';

  @override
  String get participants => '參與者';

  @override
  String get inviteFriends => '邀請朋友';

  @override
  String invited(Object count) {
    return '已邀請 $count 人';
  }

  @override
  String get pleaseEnterTitle => '請輸入標題';

  @override
  String get myContacts => '我的聯絡人';

  @override
  String get sessionExpired => '連線逾時，即將重新導向至登入頁面...';

  @override
  String get user => '用戶';

  @override
  String get month => '月';

  @override
  String get week => '週';

  @override
  String get day => '日';

  @override
  String get noEvents => '無行程';

  @override
  String eventsCount(Object count) {
    return '$count 項行程';
  }

  @override
  String get statusActive => '進行中';

  @override
  String get statusPending => '待確認';

  @override
  String get statusNotGoing => '不參加';

  @override
  String get statusNotAttend => '未出席';

  @override
  String get statusAttend => '出席';

  @override
  String get statusCancelled => '已取消';

  @override
  String get iosLimitation => 'iOS 限制';

  @override
  String get iosLimitationDesc => '由於 iOS 隱私政策限制，無法存取通話記錄。';

  @override
  String get androidOnly => '此功能僅在 Android 裝置上可用。';

  @override
  String get permissionRequired => '需要權限';

  @override
  String get permissionDesc => '需要通話記錄權限才能顯示通話歷史。';

  @override
  String get openSettings => '開啟設定';

  @override
  String get noCallLogs => '無通話記錄';

  @override
  String get incoming => '來電';

  @override
  String get outgoing => '撥出';

  @override
  String get missed => '未接';

  @override
  String get rejected => '拒接';

  @override
  String get unknown => '未知';

  @override
  String get unknownNumber => '未知號碼';

  @override
  String get today => '今天';

  @override
  String get yesterday => '昨天';

  @override
  String get hours => '小時';

  @override
  String get minutes => '分';

  @override
  String get seconds => '秒';

  @override
  String get notConnected => '未接通';

  @override
  String get selectLocation => '選擇位置';

  @override
  String get statusComingSoon => '即將開始';

  @override
  String get pleaseEnterFutureTime => '請選擇未來的時間';

  @override
  String get endTime => '結束時間';

  @override
  String get notSet => '未設定';

  @override
  String get endTimeMustBeAfterStartTime => '結束時間必須晚於開始時間';

  @override
  String get defaultNotificationMethod => '預設通知方式';
}
