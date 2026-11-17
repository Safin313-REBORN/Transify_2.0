# Transify Proguard Rules
-keepattributes *Annotation*
-keepattributes JavascriptInterface

# Keep Javascript interfaces so WebView reflection doesn't strip them
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Keep WebKit and AndroidX WebKit
-keep class androidx.webkit.** { *; }
-dontwarn androidx.webkit.**

