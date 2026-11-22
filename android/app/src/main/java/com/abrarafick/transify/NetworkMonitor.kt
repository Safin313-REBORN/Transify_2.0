package com.abrarafick.transify

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.Handler
import android.os.Looper
import android.util.Log

/**
 * NetworkMonitor — Real-Time Connectivity Listener for Transify Android.
 *
 * Provides real-time network presence and capability detection:
 * - Detects active network loss and recovery.
 * - Identifies transport type (WiFi, Cellular, Ethernet).
 * - Notifies UI to display the native offline warning banner.
 * - Prevents futile background server polling when offline.
 */
class NetworkMonitor(context: Context) {

    companion object {
        private const val TAG = "TransifyNetworkMonitor"
    }

    private val connectivityManager =
        context.applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager

    private val mainHandler = Handler(Looper.getMainLooper())
    private var isRegistered = false

    private var activeCallback: ((isOnline: Boolean, type: String) -> Unit)? = null

    val isOnline: Boolean
        get() {
            val cm = connectivityManager ?: return false
            val activeNetwork = cm.activeNetwork ?: return false
            val caps = cm.getNetworkCapabilities(activeNetwork) ?: return false
            return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                    caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
        }

    val networkType: String
        get() {
            val cm = connectivityManager ?: return "none"
            val activeNetwork = cm.activeNetwork ?: return "none"
            val caps = cm.getNetworkCapabilities(activeNetwork) ?: return "none"
            return when {
                caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cellular"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "ethernet"
                else -> "other"
            }
        }

    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            Log.d(TAG, "Network became available: $network")
            dispatchState(true)
        }

        override fun onLost(network: Network) {
            Log.w(TAG, "Network was lost: $network")
            dispatchState(false)
        }

        override fun onCapabilitiesChanged(network: Network, networkCapabilities: NetworkCapabilities) {
            val hasInternet = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            Log.d(TAG, "Network capabilities changed: hasInternet=$hasInternet")
            dispatchState(hasInternet)
        }
    }

    private fun dispatchState(isAvailable: Boolean) {
        mainHandler.post {
            val type = if (isAvailable) networkType else "none"
            activeCallback?.invoke(isAvailable, type)
        }
    }

    fun startMonitoring(listener: (isOnline: Boolean, type: String) -> Unit) {
        if (connectivityManager == null || isRegistered) return
        activeCallback = listener

        try {
            val request = NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build()

            connectivityManager.registerNetworkCallback(request, networkCallback)
            isRegistered = true
            Log.i(TAG, "Registered NetworkCallback for active connectivity monitoring")

            // Immediately dispatch initial state
            dispatchState(isOnline)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to register network callback", e)
        }
    }

    fun stopMonitoring() {
        if (!isRegistered || connectivityManager == null) return
        try {
            connectivityManager.unregisterNetworkCallback(networkCallback)
            isRegistered = false
            activeCallback = null
            Log.i(TAG, "Unregistered NetworkCallback")
        } catch (e: Exception) {
            Log.w(TAG, "Error unregistering network callback", e)
        }
    }
}
