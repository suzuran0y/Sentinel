package com.example.phonecamsender

import android.app.Activity
import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import okhttp3.*
import java.io.IOException

class SettingsActivity : AppCompatActivity() {

    private val prefs by lazy { getSharedPreferences("phonecam", MODE_PRIVATE) }
    private val okHttp = OkHttpClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val addrInput = findViewById<EditText>(R.id.addrInput)
        val btnDiscover = findViewById<Button>(R.id.btnDiscover)
        val btnTest = findViewById<Button>(R.id.btnTest)
        val btnSave = findViewById<Button>(R.id.btnSave)
        val swDebug = findViewById<Switch>(R.id.switchShowDebug)
        val swHide = findViewById<Switch>(R.id.switchHidePreview)
        val swStop = findViewById<Switch>(R.id.switchStopCamera)

        swHide.isChecked = prefs.getBoolean("hidePreview", false)
        swStop.isChecked = prefs.getBoolean("stopCamera", false)
        swStop.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) swHide.isChecked = true
        }


// Initialize the switch status
        swDebug.isChecked = prefs.getBoolean("showDebug", false)
        addrInput.setText(prefs.getString("serverInput", "") ?: "")
        btnDiscover.setOnClickListener {
            Toast.makeText(this, "Discovering...", Toast.LENGTH_SHORT).show()
            NetworkDiscover.discoverServer(
                onFound = { baseUrl ->
                    runOnUiThread {
                        addrInput.setText(NetworkDiscover.baseUrlToInput(baseUrl))
                        Toast.makeText(this, "Found: ${addrInput.text}", Toast.LENGTH_SHORT).show()
                    }
                },
                onFail = {
                    runOnUiThread {
                        Toast.makeText(this, "Discovery failed. Check that both devices are on the same network.", Toast.LENGTH_LONG).show()
                    }
                }
            )
        }

        btnTest.setOnClickListener {
            val input = addrInput.text.toString().trim()
            val baseUrl = NetworkDiscover.inputToBaseUrlOrNull(input)
            if (baseUrl == null) {
                Toast.makeText(this, "Invalid format. Please enter IP or IP:port.", Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            verifyPing(baseUrl) { ok ->
                runOnUiThread {
                    Toast.makeText(
                        this,
                        if (ok) "Connected" else "Still failed. Make sure your phone and PC are on the same network.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }

        btnSave.setOnClickListener {
            val input = addrInput.text.toString().trim()
            val baseUrl = NetworkDiscover.inputToBaseUrlOrNull(input)
            if (baseUrl == null) {
                Toast.makeText(this, "Invalid format. Please enter IP or IP:port.", Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            prefs.edit()
                .putString("serverInput", input)
                .putString("baseUrl", baseUrl)
                .putBoolean("showDebug", swDebug.isChecked)
                .putBoolean("hidePreview", swHide.isChecked)
                .putBoolean("stopCamera", swStop.isChecked)
                .apply()

            setResult(Activity.RESULT_OK)
            finish()
        }
    }

    private fun verifyPing(baseUrl: String, cb: (Boolean) -> Unit) {
        val req = Request.Builder()
            .url("${baseUrl.removeSuffix("/")}/ping")
            .get()
            .build()

        okHttp.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) = cb(false)
            override fun onResponse(call: Call, response: Response) {
                response.use { cb(it.isSuccessful) }
            }
        })
    }
}
