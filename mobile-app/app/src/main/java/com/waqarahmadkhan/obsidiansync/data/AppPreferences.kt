package com.waqarahmadkhan.obsidiansync.data

import android.content.Context
import com.waqarahmadkhan.obsidiansync.model.PairingInfo

/** Thin wrapper around SharedPreferences for the small bits of state we need to persist. */
class AppPreferences(context: Context) {
    private val prefs = context.getSharedPreferences("obsidiansync_prefs", Context.MODE_PRIVATE)

    var vaultUri: String?
        get() = prefs.getString(KEY_VAULT_URI, null)
        set(value) = prefs.edit().putString(KEY_VAULT_URI, value).apply()

    var pairing: PairingInfo?
        get() {
            val ip = prefs.getString(KEY_IP, null) ?: return null
            val port = prefs.getInt(KEY_PORT, -1)
            val token = prefs.getString(KEY_TOKEN, null) ?: return null
            val deviceName = prefs.getString(KEY_DEVICE_NAME, null) ?: return null
            if (port <= 0) return null
            return PairingInfo(ip, port, token, deviceName)
        }
        set(value) {
            val editor = prefs.edit()
            if (value == null) {
                editor.remove(KEY_IP).remove(KEY_PORT).remove(KEY_TOKEN).remove(KEY_DEVICE_NAME)
            } else {
                editor.putString(KEY_IP, value.ip)
                editor.putInt(KEY_PORT, value.port)
                editor.putString(KEY_TOKEN, value.token)
                editor.putString(KEY_DEVICE_NAME, value.deviceName)
            }
            editor.apply()
        }

    var lastSyncedAt: Long
        get() = prefs.getLong(KEY_LAST_SYNCED, 0L)
        set(value) = prefs.edit().putLong(KEY_LAST_SYNCED, value).apply()

    companion object {
        private const val KEY_VAULT_URI = "vault_uri"
        private const val KEY_IP = "pairing_ip"
        private const val KEY_PORT = "pairing_port"
        private const val KEY_TOKEN = "pairing_token"
        private const val KEY_DEVICE_NAME = "pairing_device_name"
        private const val KEY_LAST_SYNCED = "last_synced_at"
    }
}
