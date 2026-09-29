package com.waqarahmadkhan.obsidiansync.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.waqarahmadkhan.obsidiansync.model.ConnectionState
import com.waqarahmadkhan.obsidiansync.model.SyncState
import java.text.DateFormat
import java.util.Date

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    viewModel: SyncViewModel,
    onScanRequested: () -> Unit,
    onPickVaultRequested: () -> Unit
) {
    val connectionState by viewModel.connectionState.collectAsState()
    val syncState by viewModel.syncState.collectAsState()
    val vaultUri by viewModel.vaultUri.collectAsState()
    val lastSyncedAt by viewModel.lastSyncedAt.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("ObsidianSync") }) }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            ConnectionCard(connectionState, onScanRequested, onDisconnect = viewModel::disconnect)

            VaultCard(
                vaultName = viewModel.vaultDisplayName(),
                hasVault = vaultUri != null,
                onPickVaultRequested = onPickVaultRequested
            )

            SyncCard(
                connectionState = connectionState,
                syncState = syncState,
                hasVault = vaultUri != null,
                lastSyncedAt = lastSyncedAt,
                onSyncClicked = viewModel::sync
            )
        }
    }
}

@Composable
private fun ConnectionCard(
    state: ConnectionState,
    onScanRequested: () -> Unit,
    onDisconnect: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Connection", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            when (state) {
                is ConnectionState.Disconnected -> {
                    Text("Not connected to a desktop.")
                    Spacer(Modifier.height(12.dp))
                    Button(onClick = onScanRequested, modifier = Modifier.fillMaxWidth()) {
                        Icon(Icons.Filled.QrCodeScanner, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Scan QR Code")
                    }
                }
                is ConnectionState.Connecting -> {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(12.dp))
                        Text("Connecting…")
                    }
                }
                is ConnectionState.Connected -> {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Color(0xFF2E7D32))
                        Spacer(Modifier.width(8.dp))
                        Column {
                            Text("Connected to ${state.deviceName}", fontWeight = FontWeight.Medium)
                            Text(state.ip, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = onScanRequested) { Text("Re-scan") }
                        OutlinedButton(onClick = onDisconnect) { Text("Disconnect") }
                    }
                }
                is ConnectionState.Error -> {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Error, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.width(8.dp))
                        Text(state.message, color = MaterialTheme.colorScheme.error)
                    }
                    Spacer(Modifier.height(12.dp))
                    Button(onClick = onScanRequested, modifier = Modifier.fillMaxWidth()) {
                        Text("Try Again")
                    }
                }
            }
        }
    }
}

@Composable
private fun VaultCard(
    vaultName: String?,
    hasVault: Boolean,
    onPickVaultRequested: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Vault Folder", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            Text(if (hasVault) vaultName ?: "Selected" else "No folder selected yet.")
            Spacer(Modifier.height(12.dp))
            OutlinedButton(onClick = onPickVaultRequested, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Filled.Folder, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(if (hasVault) "Change Folder" else "Choose Folder")
            }
        }
    }
}

@Composable
private fun SyncCard(
    connectionState: ConnectionState,
    syncState: SyncState,
    hasVault: Boolean,
    lastSyncedAt: Long,
    onSyncClicked: () -> Unit
) {
    val canSync = connectionState is ConnectionState.Connected && hasVault && syncState !is SyncState.Syncing

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Sync", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))

            when (syncState) {
                is SyncState.Idle -> {
                    if (lastSyncedAt > 0) {
                        Text("Last synced: ${formatTimestamp(lastSyncedAt)}")
                    } else {
                        Text("Not synced yet.")
                    }
                }
                is SyncState.Syncing -> Text(syncState.message)
                is SyncState.Success -> Text(
                    "Synced ${syncState.filesUpdated} updated, ${syncState.filesDeleted} removed."
                )
                is SyncState.Error -> Text(syncState.message, color = MaterialTheme.colorScheme.error)
            }

            Spacer(Modifier.height(12.dp))
            Button(onClick = onSyncClicked, enabled = canSync, modifier = Modifier.fillMaxWidth()) {
                if (syncState is SyncState.Syncing) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Filled.Sync, contentDescription = null)
                }
                Spacer(Modifier.width(8.dp))
                Text("Sync Now")
            }
        }
    }
}

private fun formatTimestamp(millis: Long): String =
    DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(millis))
