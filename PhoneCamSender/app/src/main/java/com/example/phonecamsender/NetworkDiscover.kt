package com.example.phonecamsender

object NetworkDiscover {

    // 输入：172.16.1.2 或 172.16.1.2:8000 -> 输出 baseUrl: http://172.16.1.2:8000
    fun inputToBaseUrlOrNull(input: String): String? {
        val s = input.trim().removePrefix("http://").removePrefix("https://")
        if (s.isBlank()) return null

        val hostPort = if (s.contains(":")) s else "$s:8000"
        // 简单校验
        if (!hostPort.contains(":")) return null
        return "http://$hostPort"
    }

    // baseUrl: http://x.x.x.x:8000 -> 显示给用户：x.x.x.x:8000
    fun baseUrlToInput(baseUrl: String): String {
        return baseUrl.removePrefix("http://").removePrefix("https://").removeSuffix("/")
    }

    fun discoverServer(onFound: (String) -> Unit, onFail: () -> Unit) {
        kotlin.concurrent.thread {
            try {
                val socket = java.net.DatagramSocket().apply {
                    broadcast = true
                    soTimeout = 800
                }
                val msg = "FIND_PHONECAM_SERVER".toByteArray()
                val broadcast = java.net.InetAddress.getByName("255.255.255.255")
                val packet = java.net.DatagramPacket(msg, msg.size, broadcast, 37020)

                repeat(3) {
                    socket.send(packet)
                    try {
                        val buf = ByteArray(1024)
                        val resp = java.net.DatagramPacket(buf, buf.size)
                        socket.receive(resp)
                        val text = String(resp.data, 0, resp.length)
                        if (text.startsWith("PHONECAM_SERVER ")) {
                            val url = text.removePrefix("PHONECAM_SERVER ").trim().removeSuffix("/")
                            socket.close()
                            onFound(url)
                            return@thread
                        }
                    } catch (_: Exception) {}
                    Thread.sleep(150)
                }

                socket.close()
                onFail()
            } catch (_: Exception) {
                onFail()
            }
        }
    }
}
