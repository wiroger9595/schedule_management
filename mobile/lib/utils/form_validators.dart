import 'package:easy_localization/easy_localization.dart';

class FormValidators {
  /// Email 格式驗證
  /// 如果值為空，返回 null（允許選填）
  /// 如果格式不正確，返回錯誤訊息
  static String? validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) {
      return null; // 允許空值（選填）
    }
    
    final emailRegex = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    );
    
    if (!emailRegex.hasMatch(value.trim())) {
      return 'invalidEmailFormat'.tr();
    }
    return null;
  }
  
  /// 電話號碼驗證（台灣格式）
  /// [required] 是否為必填欄位
  static String? validatePhone(String? value, {bool required = false}) {
    if (value == null || value.trim().isEmpty) {
      return required ? 'enterPhone'.tr() : null;
    }
    
    // 移除空格、括號、破折號
    final cleaned = value.replaceAll(RegExp(r'[\s\-\(\)]'), '');
    
    // 檢查是否為數字
    if (!RegExp(r'^\d+$').hasMatch(cleaned)) {
      return 'phoneNumberOnly'.tr();
    }
    
    // 台灣手機號碼：09開頭，10碼
    // 台灣市話：2-8開頭，區碼+號碼共8-10碼
    if (cleaned.length < 8 || cleaned.length > 11) {
      return '請輸入有效的電話號碼（8-11碼）';
    }
    
    return null;
  }
  
  /// 檢查至少一項聯絡方式
  /// 確保用戶至少填寫了電話、Email 或 Line ID 其中一項
  static String? validateAtLeastOneContact({
    String? phone,
    String? email,
    String? lineId,
  }) {
    final hasPhone = phone != null && phone.trim().isNotEmpty;
    final hasEmail = email != null && email.trim().isNotEmpty;
    final hasLineId = lineId != null && lineId.trim().isNotEmpty;
    
    if (!hasPhone && !hasEmail && !hasLineId) {
      return '請至少填寫以下其中一項：電話、Email 或 Line ID';
    }
    return null;
  }
  
  /// 必填欄位驗證
  static String? validateRequired(String? value, String fieldName) {
    if (value == null || value.trim().isEmpty) {
      return '請輸入$fieldName';
    }
    return null;
  }
}
