package com.waqarahmadkhan.obsidiansync

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import com.waqarahmadkhan.obsidiansync.ui.HomeScreen
import com.waqarahmadkhan.obsidiansync.ui.SyncViewModel
import com.waqarahmadkhan.obsidiansync.ui.theme.ObsidianSyncTheme

class MainActivity : ComponentActivity() {

    private val viewModel: SyncViewModel by viewModels()

    private val scanLauncher = registerForActivityResult(ScanContract()) { result ->
        result.contents?.let { viewModel.onQrScanned(it) }
    }

    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) requestLocalNetworkAndScan() else {
            Toast.makeText(this, "Camera permission is required to scan the QR code", Toast.LENGTH_LONG).show()
        }
    }

    private val localNetworkPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) launchScanner() else {
            Toast.makeText(
                this,
                "Local network access is required to connect to your desktop",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    private val folderPickerLauncher = registerForActivityResult(
        ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        uri?.let { viewModel.onVaultFolderPicked(it) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        requestLocalNetworkPermissionIfNeeded()
        setContent {
            ObsidianSyncTheme {
                HomeScreen(
                    viewModel = viewModel,
                    onScanRequested = { requestCameraAndScan() },
                    onPickVaultRequested = { launchFolderPicker() }
                )
            }
        }
    }

    private fun requestCameraAndScan() {
        val granted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
        if (granted) requestLocalNetworkAndScan() else cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
    }

    private fun requestLocalNetworkAndScan() {
        val granted = ContextCompat.checkSelfPermission(
            this, LOCAL_NETWORK_PERMISSION
        ) == PackageManager.PERMISSION_GRANTED
        if (granted) launchScanner() else localNetworkPermissionLauncher.launch(LOCAL_NETWORK_PERMISSION)
    }

    /** On Android 17+ this permission gates any connection to a private LAN address; request it up front. */
    private fun requestLocalNetworkPermissionIfNeeded() {
        val granted = ContextCompat.checkSelfPermission(
            this, LOCAL_NETWORK_PERMISSION
        ) == PackageManager.PERMISSION_GRANTED
        if (!granted) {
            localNetworkPermissionLauncher.launch(LOCAL_NETWORK_PERMISSION)
        }
    }

    companion object {
        private const val LOCAL_NETWORK_PERMISSION = "android.permission.ACCESS_LOCAL_NETWORK"
    }

    private fun launchScanner() {
        val options = ScanOptions().apply {
            setDesiredBarcodeFormats(ScanOptions.QR_CODE)
            setPrompt("Point at the QR code on your desktop")
            setBeepEnabled(false)
            setOrientationLocked(true)
        }
        scanLauncher.launch(options)
    }

    private fun launchFolderPicker() {
        folderPickerLauncher.launch(null)
    }
}
