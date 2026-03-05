import 'package:flutter/material.dart';
import 'dart:io';

import 'dart:typed_data';

class UserAvatar extends StatelessWidget {
  final String? imageUrl;
  final File? imageFile;
  final Uint8List? imageBytes;
  final double radius;
  final Widget? fallbackWidget;

  const UserAvatar({
    Key? key,
    this.imageUrl,
    this.imageFile,
    this.imageBytes,
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
    debugPrint('UserAvatar: imageUrl=$imageUrl, imageFile=$imageFile, hasBytes=${imageBytes != null}');
    if (imageBytes != null) {
      return Image.memory(
        imageBytes!,
        fit: BoxFit.cover,
        width: radius * 2,
        height: radius * 2,
        errorBuilder: (context, error, stackTrace) {
          return _buildFallbackDetails();
        },
      );
    }
    
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
    
    if (imageUrl != null && imageUrl!.trim().isNotEmpty && imageUrl!.trim().toLowerCase() != 'null') {
      String finalUrl = imageUrl!.trim();
      
      return Image.network(
        finalUrl,
        fit: BoxFit.cover,
        width: radius * 2,
        height: radius * 2,
        errorBuilder: (context, error, stackTrace) {
          debugPrint('Error loading avatar image: $error');
          return _buildFallbackDetails();
        },
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child; // Image finished loading
          
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
