import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppTheme {
  AppTheme._();

  // ── Brand — Navy Design System ────────────────────────
  static const Color primary      = Color(0xFF1B3A6E); // Deep Navy
  static const Color primaryDark  = Color(0xFF102952); // Darker Navy
  static const Color primaryLight = Color(0xFFDEE8F8); // Navy 100

  // ── Surface ───────────────────────────────────────────
  static const Color background   = Color(0xFFF0F2F7); // Light blue-gray
  static const Color surface      = Color(0xFFFFFFFF);
  static const Color surfaceVar   = Color(0xFFF5F7FB);

  // ── App Bar ───────────────────────────────────────────
  static const Color appBarBg     = Color(0xFFFFFFFF); // White app bar

  // ── Text ──────────────────────────────────────────────
  static const Color textPrimary  = Color(0xFF1A1E2E); // Near-black
  static const Color textSecond   = Color(0xFF6B7280); // Gray 500
  static const Color textMuted    = Color(0xFF9CA3AF); // Gray 400

  // ── Border ────────────────────────────────────────────
  static const Color border       = Color(0xFFE5E7EB); // Gray 200

  // ── Status colors ─────────────────────────────────────
  static const Color statusCS  = Color(0xFF6366F1); // comingSoon  — indigo
  static const Color statusA   = Color(0xFF0EA5E9); // active      — sky
  static const Color statusP   = Color(0xFF10B981); // pending     — emerald
  static const Color statusAT  = Color(0xFF22C55E); // attend      — green
  static const Color statusNG  = Color(0xFF94A3B8); // notGoing    — slate
  static const Color statusNA  = Color(0xFFF59E0B); // notAttended — amber
  static const Color statusC   = Color(0xFFEF4444); // cancel      — red

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.light(
        primary:        primary,
        onPrimary:      Colors.white,
        secondary:      Color(0xFF0EA5E9),
        surface:        surface,
        onSurface:      textPrimary,
        outline:        border,
      ),

      // ── AppBar ──────────────────────────────────────────
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: appBarBg,
        foregroundColor: textPrimary,
        iconTheme:        IconThemeData(color: textPrimary),
        actionsIconTheme: IconThemeData(color: textPrimary),
        systemOverlayStyle: SystemUiOverlayStyle(
          statusBarBrightness:      Brightness.light,
          statusBarIconBrightness:  Brightness.dark,
        ),
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),

      // ── TabBar ──────────────────────────────────────────
      tabBarTheme: const TabBarThemeData(
        labelColor:           primary,
        unselectedLabelColor: textMuted,
        indicatorColor:       primary,
        indicatorSize:        TabBarIndicatorSize.label,
        labelStyle:           TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        unselectedLabelStyle: TextStyle(fontWeight: FontWeight.w400, fontSize: 14),
      ),

      // ── Cards ───────────────────────────────────────────
      cardTheme: CardThemeData(
        elevation: 0,
        color: surface,
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: border, width: 1),
        ),
        shadowColor: Colors.transparent,
      ),

      // ── Drawer ──────────────────────────────────────────
      drawerTheme: const DrawerThemeData(
        backgroundColor: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.horizontal(right: Radius.circular(0)),
        ),
      ),

      // ── Bottom Navigation Bar ────────────────────────────
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: primary,
        unselectedItemColor: textMuted,
        selectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: TextStyle(fontSize: 11),
        type: BottomNavigationBarType.fixed,
        elevation: 8,
      ),

      // ── Input ───────────────────────────────────────────
      inputDecorationTheme: InputDecorationTheme(
        filled: false,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: border, width: 1.5),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: border, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        labelStyle: const TextStyle(color: textSecond),
        hintStyle: const TextStyle(color: textMuted),
      ),

      // ── Buttons — pill shape ─────────────────────────────
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          elevation: 2,
          shadowColor: primary.withOpacity(0.35),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: const StadiumBorder(),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: const BorderSide(color: primary, width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: const StadiumBorder(),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),

      // ── FAB ─────────────────────────────────────────────
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: primary,
        foregroundColor: Colors.white,
        elevation: 4,
        shape: CircleBorder(),
      ),

      // ── List Tile ───────────────────────────────────────
      listTileTheme: const ListTileThemeData(
        contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 4),
        iconColor: textSecond,
        titleTextStyle: TextStyle(color: textPrimary, fontSize: 15, fontWeight: FontWeight.w500),
        subtitleTextStyle: TextStyle(color: textSecond, fontSize: 13),
      ),

      // ── Divider ─────────────────────────────────────────
      dividerTheme: const DividerThemeData(
        color: border,
        thickness: 1,
        space: 1,
      ),

      // ── Chip ────────────────────────────────────────────
      chipTheme: ChipThemeData(
        backgroundColor: surface,
        side: const BorderSide(color: border),
        labelStyle: const TextStyle(fontSize: 12, color: textPrimary),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        shape: const StadiumBorder(side: BorderSide(color: border)),
      ),
    );
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        brightness: Brightness.dark,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
      ),
    );
  }
}
