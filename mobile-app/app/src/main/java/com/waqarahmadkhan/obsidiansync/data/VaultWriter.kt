package com.waqarahmadkhan.obsidiansync.data

import android.content.Context
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import org.json.JSONObject
import java.io.File

/**
 * Writes synced files into the user's chosen vault folder (a SAF tree Uri) and keeps a small
 * local record of what was last written, so repeat syncs only touch files that changed.
 */
class VaultWriter(private val context: Context, private val treeUri: Uri) {

    private val root: DocumentFile =
        DocumentFile.fromTreeUri(context, treeUri) ?: error("Cannot open vault folder")

    private val stateFile = File(context.filesDir, "sync_state.json")

    fun loadLocalState(): MutableMap<String, String> {
        if (!stateFile.exists()) return mutableMapOf()
        return try {
            val json = JSONObject(stateFile.readText())
            val map = mutableMapOf<String, String>()
            json.keys().forEach { key -> map[key] = json.getString(key) }
            map
        } catch (e: Exception) {
            mutableMapOf()
        }
    }

    fun saveLocalState(state: Map<String, String>) {
        val json = JSONObject()
        state.forEach { (k, v) -> json.put(k, v) }
        stateFile.writeText(json.toString())
    }

    /** Finds (or creates) the DocumentFile for a manifest-relative path, creating parent dirs. */
    fun getOrCreateFile(relPath: String, mimeType: String = "application/octet-stream"): DocumentFile {
        val parts = relPath.split("/")
        var dir = root
        for (dirName in parts.dropLast(1)) {
            dir = dir.findFile(dirName)?.takeIf { it.isDirectory }
                ?: dir.createDirectory(dirName)
                ?: error("Cannot create directory $dirName")
        }
        val fileName = parts.last()
        return dir.findFile(fileName) ?: dir.createFile(mimeType, fileName)
            ?: error("Cannot create file $fileName")
    }

    fun writeBytes(relPath: String, bytes: ByteArray) {
        val doc = getOrCreateFile(relPath)
        context.contentResolver.openOutputStream(doc.uri, "wt")?.use { out ->
            out.write(bytes)
        }
    }

    fun deleteFile(relPath: String) {
        val parts = relPath.split("/")
        var dir: DocumentFile? = root
        for (dirName in parts.dropLast(1)) {
            dir = dir?.findFile(dirName)
            if (dir == null) return
        }
        dir?.findFile(parts.last())?.delete()
    }

    fun vaultDisplayName(): String = root.name ?: "Vault"
}
