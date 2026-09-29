package com.waqarahmadkhan.obsidiansync.model

/** Connection info decoded from the desktop app's pairing QR code. */
data class PairingInfo(
    val ip: String,
    val port: Int,
    val token: String,
    val deviceName: String
) {
    val baseUrl: String get() = "http://$ip:$port"
}

/** A single file entry as reported by the desktop's /manifest endpoint. */
data class ManifestEntry(
    val path: String,
    val hash: String,
    val size: Long,
    val mtime: Double
)

sealed interface ConnectionState {
    data object Disconnected : ConnectionState
    data object Connecting : ConnectionState
    data class Connected(val deviceName: String, val ip: String) : ConnectionState
    data class Error(val message: String) : ConnectionState
}

sealed interface SyncState {
    data object Idle : SyncState
    data class Syncing(val message: String) : SyncState
    data class Success(val filesUpdated: Int, val filesDeleted: Int) : SyncState
    data class Error(val message: String) : SyncState
}
