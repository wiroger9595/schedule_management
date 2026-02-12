class User {
  final String? userId;
  final String? email;
  final String? fullName;
  final String? phone;
  final String? lineId;
  final String? language;
  final String? profileImagePath;
  final String? status;

  User({
    this.userId,
    this.email,
    this.fullName,
    this.phone,
    this.lineId,
    this.language,
    this.profileImagePath,
    this.status,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      userId: json['user_id'] as String?,
      email: json['email'] as String?,
      fullName: json['full_name'] as String?,
      phone: json['phone'] as String?,
      lineId: json['line_id'] as String?,
      language: json['language'] as String?,
      profileImagePath: json['profile_image_path'] as String?,
      status: json['status'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'email': email,
      'full_name': fullName,
      'phone': phone,
      'line_id': lineId,
      'language': language,
      'profile_image_path': profileImagePath,
      'status': status,
    };
  }

  User copyWith({
    String? userId,
    String? email,
    String? fullName,
    String? phone,
    String? lineId,
    String? language,
    String? profileImagePath,
    String? status,
  }) {
    return User(
      userId: userId ?? this.userId,
      email: email ?? this.email,
      fullName: fullName ?? this.fullName,
      phone: phone ?? this.phone,
      lineId: lineId ?? this.lineId,
      language: language ?? this.language,
      profileImagePath: profileImagePath ?? this.profileImagePath,
      status: status ?? this.status,
    );
  }
}
