package com.waqarahmadkhan.obsidiansync.network

import com.waqarahmadkhan.obsidiansync.model.ManifestEntry
import com.waqarahmadkhan.obsidiansync.model.PairingInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class SyncClient(private val pairing: PairingInfo) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    /** Confirms the desktop is reachable and the token is accepted. Returns the desktop's device name. */
    suspend fun pair(): Result<String> = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder()
                .url("${pairing.baseUrl}/pair?token=${pairing.token}")
                .build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) error("Pairing failed: HTTP ${response.code}")
                val body = JSONObject(response.body?.string() ?: "{}")
                body.getString("device_name")
            }
        }
    }

    data class Manifest(val vaultName: String, val files: List<ManifestEntry>)

    suspend fun fetchManifest(): Result<Manifest> = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder()
                .url("${pairing.baseUrl}/manifest?token=${pairing.token}")
                .build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) error("Manifest fetch failed: HTTP ${response.code}")
                val body = JSONObject(response.body?.string() ?: "{}")
                val vaultName = body.optString("vault_name", "Vault")
                val filesJson = body.getJSONArray("files")
                val files = buildList {
                    for (i in 0 until filesJson.length()) {
                        val entry = filesJson.getJSONObject(i)
                        add(
                            ManifestEntry(
                                path = entry.getString("path"),
                                hash = entry.getString("hash"),
                                size = entry.getLong("size"),
                                mtime = entry.getDouble("mtime")
                            )
                        )
                    }
                }
                Manifest(vaultName, files)
            }
        }
    }

    /** Tells the desktop how many files are about to be downloaded, for an accurate progress bar. */
    suspend fun notifySyncBegin(total: Int) = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder()
                .url("${pairing.baseUrl}/sync-begin?token=${pairing.token}&total=$total")
                .build()
            client.newCall(request).execute().close()
        }
    }

    /** Tells the desktop the sync run finished, so it can stop showing "Syncing…". Best-effort. */
    suspend fun notifySyncComplete(status: String, updated: Int, deleted: Int, message: String = "") =
        withContext(Dispatchers.IO) {
            runCatching {
                val encodedMessage = java.net.URLEncoder.encode(message, "UTF-8")
                val request = Request.Builder()
                    .url(
                        "${pairing.baseUrl}/sync-complete?token=${pairing.token}" +
                            "&status=$status&updated=$updated&deleted=$deleted&message=$encodedMessage"
                    )
                    .build()
                client.newCall(request).execute().close()
            }
        }

    suspend fun downloadFile(relPath: String): Result<ByteArray> = withContext(Dispatchers.IO) {
        runCatching {
            val encodedPath = java.net.URLEncoder.encode(relPath, "UTF-8")
            val request = Request.Builder()
                .url("${pairing.baseUrl}/file?token=${pairing.token}&path=$encodedPath")
                .build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) error("Download failed for $relPath: HTTP ${response.code}")
                response.body?.bytes() ?: error("Empty response body for $relPath")
            }
        }
    }
}
