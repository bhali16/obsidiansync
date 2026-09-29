package com.waqarahmadkhan.obsidiansync.ui

import android.app.Application
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.waqarahmadkhan.obsidiansync.data.AppPreferences
import com.waqarahmadkhan.obsidiansync.data.VaultWriter
import com.waqarahmadkhan.obsidiansync.model.ConnectionState
import com.waqarahmadkhan.obsidiansync.model.PairingInfo
import com.waqarahmadkhan.obsidiansync.model.SyncState
import com.waqarahmadkhan.obsidiansync.network.SyncClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

class SyncViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = AppPreferences(application)

    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _syncState = MutableStateFlow<SyncState>(SyncState.Idle)
    val syncState: StateFlow<SyncState> = _syncState.asStateFlow()

    private val _vaultUri = MutableStateFlow(prefs.vaultUri?.let { Uri.parse(it) })
    val vaultUri: StateFlow<Uri?> = _vaultUri.asStateFlow()

    private val _lastSyncedAt = MutableStateFlow(prefs.lastSyncedAt)
    val lastSyncedAt: StateFlow<Long> = _lastSyncedAt.asStateFlow()

    private var pairing: PairingInfo? = prefs.pairing

    init {
        pairing?.let { _connectionState.value = ConnectionState.Connecting }
        pairing?.let { reconnect(it) }
    }

    fun vaultDisplayName(): String? {
        val uri = _vaultUri.value ?: return null
        return DocumentFile.fromTreeUri(getApplication(), uri)?.name
    }

    fun onVaultFolderPicked(uri: Uri) {
        val contentResolver = getApplication<Application>().contentResolver
        contentResolver.takePersistableUriPermission(
            uri,
            android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION or
                android.content.Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )
        prefs.vaultUri = uri.toString()
        _vaultUri.value = uri
    }

    /** Parses the raw QR payload and attempts to pair with the desktop app. */
    fun onQrScanned(rawValue: String) {
        val info = parsePairingPayload(rawValue) ?: run {
            _connectionState.value = ConnectionState.Error("Unrecognized QR code")
            return
        }
        reconnect(info)
    }

    private fun reconnect(info: PairingInfo) {
        _connectionState.value = ConnectionState.Connecting
        viewModelScope.launch {
            val client = SyncClient(info)
            val result = client.pair()
            result.onSuccess { deviceName ->
                pairing = info
                prefs.pairing = info
                _connectionState.value = ConnectionState.Connected(deviceName, info.ip)
            }.onFailure { e ->
                _connectionState.value = ConnectionState.Error(e.message ?: "Could not connect")
            }
        }
    }

    fun disconnect() {
        pairing = null
        prefs.pairing = null
        _connectionState.value = ConnectionState.Disconnected
        _syncState.value = SyncState.Idle
    }

    fun sync() {
        val info = pairing ?: return
        val vaultUri = _vaultUri.value ?: run {
            _syncState.value = SyncState.Error("Choose a vault folder first")
            return
        }
        viewModelScope.launch {
            _syncState.value = SyncState.Syncing("Fetching file list…")
            val app = getApplication<Application>()
            val client = SyncClient(info)

            val manifestResult = client.fetchManifest()
            val manifest = manifestResult.getOrElse { e ->
                val msg = e.message ?: "Failed to fetch manifest"
                _syncState.value = SyncState.Error(msg)
                client.notifySyncComplete(status = "error", updated = 0, deleted = 0, message = msg)
                return@launch
            }

            val writer = VaultWriter(app, vaultUri)
            val localState = writer.loadLocalState()
            val remotePaths = manifest.files.map { it.path }.toSet()

            val toUpdate = manifest.files.filter { localState[it.path] != it.hash }
            val toDelete = localState.keys.filter { it !in remotePaths }

            var updated = 0
            var deleted = 0

            client.notifySyncBegin(toUpdate.size)

            for ((index, entry) in toUpdate.withIndex()) {
                _syncState.value = SyncState.Syncing("Syncing ${index + 1}/${toUpdate.size}: ${entry.path}")
                val bytesResult = client.downloadFile(entry.path)
                val bytes = bytesResult.getOrElse { e ->
                    val msg = "Failed on ${entry.path}: ${e.message}"
                    _syncState.value = SyncState.Error(msg)
                    client.notifySyncComplete(status = "error", updated = updated, deleted = deleted, message = msg)
                    return@launch
                }
                withContext(Dispatchers.IO) { writer.writeBytes(entry.path, bytes) }
                localState[entry.path] = entry.hash
                updated++
            }

            for (path in toDelete) {
                withContext(Dispatchers.IO) { writer.deleteFile(path) }
                localState.remove(path)
                deleted++
            }

            withContext(Dispatchers.IO) { writer.saveLocalState(localState) }

            val now = System.currentTimeMillis()
            prefs.lastSyncedAt = now
            _lastSyncedAt.value = now
            _syncState.value = SyncState.Success(updated, deleted)
            client.notifySyncComplete(status = "success", updated = updated, deleted = deleted)
        }
    }

    private fun parsePairingPayload(raw: String): PairingInfo? {
        return try {
            val json = JSONObject(raw)
            PairingInfo(
                ip = json.getString("ip"),
                port = json.getInt("port"),
                token = json.getString("token"),
                deviceName = json.optString("device_name", "Mac")
            )
        } catch (e: Exception) {
            null
        }
    }
}
