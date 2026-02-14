import 'package:flutter/material.dart';

import 'dart:io';

class UserAvatar extends StatelessWidget {
  final String? imageUrl;
  final File? imageFile;
  final double radius;
  final Widget? fallbackWidget;

  const UserAvatar({
    Key? key,
    this.imageUrl,
    this.imageFile,
    this.radius = 20,
    this.fallbackWidget,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return CircleAvatar(
      radius: radius,
      backgroundColor: Colors.grey[200],
      child: ClipOval(
        child: SizedBox(
          width: radius * 2,
          height: radius * 2,
          child: _buildImage(),
          ),
      ),
    );
  }

  Widget _buildImage() {
    if (imageFile != null) {
      return Image.file(
        imageFile!,
        fit: BoxFit.cover,
        width: radius * 2,
        height: radius * 2,
        errorBuilder: (context, error, stackTrace) {
          return _buildFallbackDetails();
        },
      );
    }
    
    if (imageUrl != null && imageUrl!.isNotEmpty) {
      return Image.network(
        imageUrl!,
        fit: BoxFit.cover,
        width: radius * 2,
        height: radius * 2,
        errorBuilder: (context, error, stackTrace) {
          return _buildFallbackDetails();
        },
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child;
          return Center(
            child: CircularProgressIndicator(
              value: loadingProgress.expectedTotalBytes != null
                  ? loadingProgress.cumulativeBytesLoaded /
                      loadingProgress.expectedTotalBytes!
                  : null,
              strokeWidth: 2,
            ),
          );
        },
      );
    }
    return _buildFallbackDetails();
  }

  Widget _buildFallbackDetails() {
    // Try to load asset image first
    return Image.asset(
      'assets/images/default_profile.png',
      fit: BoxFit.cover,
      width: radius * 2,
      height: radius * 2,
      errorBuilder: (context, error, stackTrace) {
        // If asset missing, show Icon
        if (fallbackWidget != null) return fallbackWidget!;
        return Icon(
          Icons.person,
          size: radius * 1.2,
          color: Colors.purple[700],
        );
      },
    );
  }
}
