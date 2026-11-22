import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val transifyBaseUrlProp: String = (
    project.findProperty("TRANSIFY_BASE_URL") as? String
        ?: System.getenv("TRANSIFY_BASE_URL")
        ?: ""
).trim()

val escapedBaseUrl = transifyBaseUrlProp.replace("\\", "\\\\").replace("\"", "\\\"")

val externalSigningPropsFile = (
    project.findProperty("SIGNING_PROPERTIES_PATH") as? String
        ?: System.getenv("SIGNING_PROPERTIES_PATH")
        ?: "${System.getProperty("user.home")}/.transify_release/release-signing.properties"
).let { File(it) }

val signingFileProperties = Properties()
if (externalSigningPropsFile.exists()) {
    externalSigningPropsFile.inputStream().use { signingFileProperties.load(it) }
}

fun resolveSigningProperty(name: String): String? {
    return (project.findProperty(name) as? String)
        ?: System.getenv(name)
        ?: signingFileProperties.getProperty(name)
}

android {
    namespace = "com.abrarafick.transify"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.abrarafick.transify"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        buildConfigField("String", "TRANSIFY_BASE_URL", "\"$escapedBaseUrl\"")
    }

    signingConfigs {
        create("release") {
            val keystorePath = resolveSigningProperty("KEYSTORE_PATH")
                ?: "${System.getProperty("user.home")}/.transify_release/transify-release.keystore"
            val keystoreFile = File(keystorePath)

            val storePasswordValue = resolveSigningProperty("KEYSTORE_PASSWORD")
            val keyAliasValue = resolveSigningProperty("KEY_ALIAS") ?: "transify"
            val keyPasswordValue = resolveSigningProperty("KEY_PASSWORD") ?: storePasswordValue
            if (keystoreFile.exists() && !storePasswordValue.isNullOrBlank() && !keyPasswordValue.isNullOrBlank()) {
                this.storeFile = keystoreFile
                this.storePassword = storePasswordValue
                this.keyAlias = keyAliasValue
                this.keyPassword = keyPasswordValue
            }
        }
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
            applicationIdSuffix = ""
            versionNameSuffix = "-debug"
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

// Strict Release guards for URL validation and Signing Credential enforcement
gradle.taskGraph.whenReady {
    val isReleaseBuild = hasTask(":app:assembleRelease") || hasTask(":app:bundleRelease")
    if (isReleaseBuild) {
        val releaseConfig = android.signingConfigs.getByName("release")
        val store = releaseConfig.storeFile
        if (store == null || !store.exists() || releaseConfig.storePassword.isNullOrBlank() || releaseConfig.keyPassword.isNullOrBlank()) {
            throw GradleException(
                "Release build failed: Required signing credentials are absent or keystore file does not exist. " +
                "Please configure KEYSTORE_PASSWORD and KEY_PASSWORD via environment variables, " +
                "Gradle project properties (-PKEYSTORE_PASSWORD=...), or ~/.transify_release/release-signing.properties."
            )
        }

        if (transifyBaseUrlProp.isBlank()) {
            throw GradleException(
                "TRANSIFY_BASE_URL must be specified for Release builds. " +
                "Provide -PTRANSIFY_BASE_URL=https://your-production-domain.com or set the TRANSIFY_BASE_URL environment variable."
            )
        }
        if (!transifyBaseUrlProp.startsWith("https://", ignoreCase = true)) {
            throw GradleException(
                "TRANSIFY_BASE_URL must use HTTPS for Release builds: '$transifyBaseUrlProp'"
            )
        }
        val lower = transifyBaseUrlProp.lowercase()
        if (lower.contains("localhost") || lower.contains("127.0.0.1") || lower.contains("10.0.2.2") || lower.contains("placeholder") || lower.contains("example.com")) {
            throw GradleException(
                "TRANSIFY_BASE_URL for Release builds cannot be a localhost, loopback, or placeholder URL: '$transifyBaseUrlProp'"
            )
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.9.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.webkit:webkit:1.11.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}
