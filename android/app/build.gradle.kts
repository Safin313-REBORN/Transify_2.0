import java.util.Properties
import java.nio.file.Files
import java.nio.file.attribute.PosixFilePermission

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

// Strict security: Credential resolution ONLY via environment variables or secure external properties file (mode 0600).
// Command-line -P project properties for credentials are explicitly rejected.
val externalSigningPropsFile = (
    System.getenv("SIGNING_PROPERTIES_PATH")
        ?: "${System.getProperty("user.home")}/.transify_release/release-signing.properties"
).let { File(it) }

// Enforce restrictive POSIX permissions before reading secrets from disk.
fun requirePosixMode(file: File, expected: Set<PosixFilePermission>, description: String) {
    try {
        val actual = Files.getPosixFilePermissions(file.toPath())
        if (actual != expected) {
            throw GradleException(
                "$description has insecure POSIX permissions; expected owner-only access. Refusing to read signing secrets."
            )
        }
    } catch (e: UnsupportedOperationException) {
        throw GradleException(
            "The filesystem does not support POSIX permission checks for $description; refusing to read signing secrets.",
            e
        )
    }
}

val signingFileProperties = Properties()
if (externalSigningPropsFile.exists()) {
    if (!externalSigningPropsFile.isFile) {
        throw GradleException("SIGNING_PROPERTIES_PATH must point to a regular file.")
    }
    val signingDirectory = externalSigningPropsFile.absoluteFile.parentFile
        ?: throw GradleException("Signing properties file must have a parent directory.")
    requirePosixMode(
        signingDirectory,
        setOf(
            PosixFilePermission.OWNER_READ,
            PosixFilePermission.OWNER_WRITE,
            PosixFilePermission.OWNER_EXECUTE
        ),
        "Signing properties parent directory"
    )
    requirePosixMode(
        externalSigningPropsFile,
        setOf(PosixFilePermission.OWNER_READ, PosixFilePermission.OWNER_WRITE),
        "Signing properties file"
    )
    externalSigningPropsFile.inputStream().use { signingFileProperties.load(it) }
}

fun resolveSigningProperty(name: String): String? {
    return System.getenv(name) ?: signingFileProperties.getProperty(name)
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
        create("directRelease") {
            val keystorePath = resolveSigningProperty("DIRECT_KEYSTORE_PATH")
                ?: resolveSigningProperty("KEYSTORE_PATH")
                ?: "${System.getProperty("user.home")}/.transify_release/transify-release.keystore"
            val keystoreFile = File(keystorePath)

            val storePasswordValue = resolveSigningProperty("DIRECT_KEYSTORE_PASSWORD")
                ?: resolveSigningProperty("KEYSTORE_PASSWORD")
            val keyAliasValue = resolveSigningProperty("DIRECT_KEY_ALIAS")
                ?: resolveSigningProperty("KEY_ALIAS") ?: "transify"
            val keyPasswordValue = resolveSigningProperty("DIRECT_KEY_PASSWORD")
                ?: resolveSigningProperty("KEY_PASSWORD") ?: storePasswordValue

            if (keystoreFile.exists() && !storePasswordValue.isNullOrBlank() && !keyPasswordValue.isNullOrBlank()) {
                this.storeFile = keystoreFile
                this.storePassword = storePasswordValue
                this.keyAlias = keyAliasValue
                this.keyPassword = keyPasswordValue
            }
        }

        create("playRelease") {
            val keystorePath = resolveSigningProperty("PLAY_KEYSTORE_PATH")
                ?: resolveSigningProperty("KEYSTORE_PATH")
                ?: "${System.getProperty("user.home")}/.transify_release/transify-release.keystore"
            val keystoreFile = File(keystorePath)

            val storePasswordValue = resolveSigningProperty("PLAY_KEYSTORE_PASSWORD")
                ?: resolveSigningProperty("KEYSTORE_PASSWORD")
            val keyAliasValue = resolveSigningProperty("PLAY_KEY_ALIAS")
                ?: resolveSigningProperty("KEY_ALIAS") ?: "transify"
            val keyPasswordValue = resolveSigningProperty("PLAY_KEY_PASSWORD")
                ?: resolveSigningProperty("KEY_PASSWORD") ?: storePasswordValue

            if (keystoreFile.exists() && !storePasswordValue.isNullOrBlank() && !keyPasswordValue.isNullOrBlank()) {
                this.storeFile = keystoreFile
                this.storePassword = storePasswordValue
                this.keyAlias = keyAliasValue
                this.keyPassword = keyPasswordValue
            }
        }
    }

    flavorDimensions += "distribution"
    productFlavors {
        create("direct") {
            dimension = "distribution"
            signingConfig = signingConfigs.getByName("directRelease")
        }
        create("play") {
            dimension = "distribution"
            signingConfig = signingConfigs.getByName("playRelease")
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
    val isDirectRelease = hasTask(":app:assembleDirectRelease") || hasTask(":app:bundleDirectRelease")
    val isPlayRelease = hasTask(":app:assemblePlayRelease") || hasTask(":app:bundlePlayRelease")
    val isGenericRelease = hasTask(":app:assembleRelease") || hasTask(":app:bundleRelease")

    if (isDirectRelease || isPlayRelease || isGenericRelease) {
        val directConfig = android.signingConfigs.getByName("directRelease")
        val playConfig = android.signingConfigs.getByName("playRelease")

        if (isDirectRelease || isGenericRelease) {
            val store = directConfig.storeFile
            if (store == null || !store.exists() || directConfig.storePassword.isNullOrBlank() || directConfig.keyPassword.isNullOrBlank()) {
                throw GradleException(
                    "Direct release build failed: Required signing credentials are absent or keystore file does not exist. " +
                    "Credentials must be supplied strictly via environment variables (KEYSTORE_PASSWORD, KEY_PASSWORD) " +
                    "or ~/.transify_release/release-signing.properties (mode 0600). Command-line -P arguments are forbidden."
                )
            }
        }

        if (isPlayRelease || isGenericRelease) {
            val store = playConfig.storeFile
            if (store == null || !store.exists() || playConfig.storePassword.isNullOrBlank() || playConfig.keyPassword.isNullOrBlank()) {
                throw GradleException(
                    "Play release build failed: Required signing credentials are absent or keystore file does not exist. " +
                    "Credentials must be supplied strictly via environment variables (KEYSTORE_PASSWORD, KEY_PASSWORD) " +
                    "or ~/.transify_release/release-signing.properties (mode 0600). Command-line -P arguments are forbidden."
                )
            }
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
