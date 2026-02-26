
<a id="top"></a>

# CamFlow 使用说明

[![Version](https://img.shields.io/badge/version-v1.0.0-black)](#)
[![Android](https://img.shields.io/badge/Android-8.0%2B-green)](CamFlow_UserGuide_CN.md)
[![Role](https://img.shields.io/badge/role-Client-blue)](README_CN.md)
[![Protocol](https://img.shields.io/badge/protocol-HTTP%20Upload-orange)](#sec42)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#sec54)

🌐 **语言** --- [🇨🇳 中文](CamFlow_UserGuide_CN.md) | [🇺🇸 English](CamFlow_UserGuide.md)

> CamFlow 是 Sentinel 系统的 Android 端“图像采集与发送”子模块，安装该应用是部署使用 Sentinel（PC 端程序 + Web Dashboard）的前置步骤。该使用说明主要方便使用者了解该程序功能信息与用法、复现部署流程与解决常见故障。

---

## 目录

- [1. 项目介绍](#sec1)
  - [1.1. 定位](#sec11)
  - [1.2. 功能概述](#sec12)
  - [1.3. 安装方式](#sec13)

- [2. 使用流程](#sec2)
  - [2.1. 启动与界面](#sec21)
  - [2.2. 连接服务器](#sec22)
  - [2.3. 设置页](#sec23)
  - [2.4. 使用步骤](#sec24)

- [3. 常见问题](#sec3)

- [4. 开发者文档](#sec4)
  - [4.1. 实现框架](#sec41)
  - [4.2. 开发 API 说明](#sec42)

- [5. 版本信息与项目说明](#sec5)
  - [5.1 系统版本信息](#sec51)
  - [5.2 测试环境说明](#sec52)
  - [5.3 后续规划](#sec53)
  - [5.4 使用与授权说明](#sec54)

---

<a id="sec1"></a>

## 1. 项目介绍 [⌃](#top)

<a id="sec11"></a>

### 1.1. 定位 [⌃](#top)

Sentinel 系统由 PC 端服务、Web Dashboard 与可选 AI 监测模块构成。CamFlow 作为移动端采集器，负责将手机摄像头实时画面以稳定、可控的速率上传至 PC 端服务，为后续的实时预览、录制与事件分析提供原始数据输入。

项目实行**移动端输入，PC 端计算与管理**的分层设计：当前 CamFlow 版本在项目整体工程上主要负责摄像头采集、编码（JPEG）、网络上传、服务器发现/连接状态提示、运行模式开关（预览隐藏/停止采集）。其余功能如视频落盘、事件检测、AI 推理等由 PC 端承担。这样便于降低移动端复杂度与维护成本。

CamFlow 与 PC 端服务器共同构成 Sentinel 系统：

- 📱 Android 端：负责图像采集与上传  
- 🖥 PC 端：负责视频处理、录制、AI 分析与可视化展示  

> 📘 关于完整系统架构与部署方式，请参阅：👉 **[Sentinel 主系统说明](README.md)**

---

<table>
<tr>
<td width="33%">

#### 🔧 工程方向

- 分布式视频数据采集架构设计  
- 局域网自动发现机制  
- 轻量级图像帧上传协议  
- 客户端运行状态管理  

</td>

<td width="33%">

#### 🧠 智能系统方向

- AI 监控与后端分析管线整合  
- 分层触发式视觉处理机制  
- 移动端与多模态模型协作  
- 实时视觉系统性能优化  

</td>

<td width="33%">

#### 本项目可作为：

- 工程实践项目示例
- Android 摄像设备调用模板
- 研究型视觉系统原型  
- AI 视频分析前端数据输入模块

</td>
</tr>
</table>

---
<a id="sec12"></a>

### 1.2. 功能概述 [⌃](#top)

CamFlow 主要功能包括：

1. **摄像头实时采集与发送**
   - 使用 Android 摄像头采集画面；
   - 将帧编码为 JPEG；
   - 通过 HTTP 上传至 PC 端服务接口（`/upload`）。

2. **服务器自动发现**
   - 通过局域网 UDP 广播尝试发现可用的 Sentinel PC 端服务；
   - 若发现失败，自动降级为手动输入服务器地址。

3. **连接测试与状态可视化**
   - 提供连接状态（Status/Server）显示；
   - 设置页提供 “Test connection” 用于快速验证服务器是否可达（通常对应 `/ping`）。

4. **运行开关与可部署性增强**
   - **Show debug info**：显示调试信息（用于现场部署快速判断是否连接、间隔参数等）；
   - **Hide camera preview**：隐藏画面（黑屏）但继续上传，减少视觉暴露，辅助隐私/部署；
   - **Stop camera**：停止采集与上传，用于省电或临时暂停输入。

---

<a id="sec13"></a>

### 1.3. 安装方式 [⌃](#top)

#### 1.3.1. 普通用户安装（APK 安装包）
> 适用于“使用者/部署者”。

1. 在 GitHub 项目的 **Releases** 页面下载 `CamFlow-v1.0.0-beta.apk`（未来你发布后将提供）。
2. 安装并打开 CamFlow。
3. 首次启动会请求摄像头权限，点击允许。

#### 1.3.2. 开发/调试安装（Android Studio）
> 适用于“开发者/维护者”。

1. 使用 Android Studio 打开 CamFlow 工程；
2. 连接手机并开启 USB 调试；
3. Run 运行到设备。

---

<a id="sec2"></a>

## 2. 使用流程 [⌃](#top)

### 2.1. 启动与界面 [⌃](#top)
打开 CamFlow 后，进入主界面。若尚未连接服务器，通常显示为未连接状态（如图1）。
<table align="center">
  <tr>
    <td align="center">
      <img src="assets/app_main_page.jpg" width="250"><br>
      <b>图 1 - 主界面（未连接状态）</b><br></td>
    <td align="center">
      <img src="assets/app_failed_hint.jpg" width="250"><br>
      <b>图 2 - 自动发现失败提示</b><br></td>
    <td align="center">
      <img src="assets/app_setting_page.jpg" width="250"><br>
      <b>图 3 - 设置页</b><br>
    </td>
  </tr>
</table>

#### 主界面字段解释：

| 字段 | 可能状态 | 语义解释 | 触发场景 |
|------|---------------|--------------|--------------|
| **Status** | Not connected | 尚未建立有效服务器连接 | 首次启动 / 未配置服务器 |
|  | Discovering server... | 正在进行局域网自动发现 | 点击 Auto discover 后 |
|  | Connecting... | 正在尝试连接服务器 | 手动输入地址后 |
|  | Connected | 已成功连接并通过可达性验证 | `/ping` 成功 |
|  **Server**| Not connected | 当前无可用服务器地址 | 未配置 / 连接失败 |
|  | xxx.xxx.xxx.xxx(:xxxx) | 已识别/保存服务器 IP (端口) | 自动发现成功 / 手动输入 |
| **Mode** | Normal | 正常采集并上传，显示预览 | 正常模式 |
|  | Hidden Preview | 画面隐藏但仍上传 | 开启 Hide camera preview |
|  | Stopped | 停止采集与上传 | 开启 Stop camera |
| **Interval** | 120ms | 默认发送间隔 | 默认配置 |
|  | >120ms | 较低帧率模式 | 调整发送间隔（开发选项） |

---

<a id="sec22"></a>

### 2.2. 连接服务器 [⌃](#top)

#### 2.2.1 自动发现

当 CamFlow 未配置服务器地址时，会尝试在局域网内自动发现服务器，且状态会显示为：`Discovering server...`

自动发现成功后，CamFlow 会填入服务器地址并进入可连接/上传状态（以具体网络环境为准：可能直接连接，也可能需用户确认保存）。

---

#### 2.2.2. 手动输入
若自动发现服务器失败，CamFlow 会弹出提示框（如图2）要求用户手动输入服务器地址。

提示框含义与输入规范：

- **Connection failed / Could not find the server automatically**
  - 说明局域网自动发现功能未得到响应。

- **Enter IP address**
  - 输入服务器 IP（若非默认端口可附带输入）。
  - 格式举例：
    - `192.168.1.10`（默认端口将被自动补全，通常为 `8000`）
    - `192.168.1.10:xxxx`（显式指定端口）

- **Connect**
  - 连接测试。若连接后 Dashboard 仍无画面，优先检查 PC 端是否启用了 ingest（接收开关）以及防火墙端口。

---

<a id="sec23"></a>

### 2.3. 设置页 [⌃](#top)
点击 **主界面右上角** 进入设置页（如图3），完成服务器配置、连接测试与运行开关设置。

#### 设置页字段定义与功能说明

| 字段 | 类型 | 格式 | 功能说明 |
|------|------|---------------|----------|
| Server address | 文本输入 | IPv4 或 IPv4:Port | 指定目标服务器地址，手动连接服务器 |

---

| 按钮 | 触发 | 状态 | 功能说明 |
|------|------|---------------|----------|
| Auto discover | 点击 | 触发一次发现流程 | 在局域网中广播寻找服务器，尝试部署 |
| Test connection | 点击 | 成功 / 失败 | 向服务器发送可达性测试请求（如 `/ping`）|
| Save | 点击 | 保存成功 | 使用当前服务器地址与设置 |

---

| 开关 | 状态 | 系统行为 | 设计目的 |
|----------|------|----------|----------|
| Show debug info | ON / OFF | 在主界面显示信息 | 方便部署调试 |
| Hide camera preview | ON / OFF | 隐藏摄像头画面但继续上传 | 关闭显示 / 减少干扰 |
| Stop camera | ON / OFF | 停止画面采集与上传 | 降低功耗 / 临时暂停 |

>  Stop camera = `ON` 时，系统会自动启用 Hide preview，避免画面残留。

---

<a id="sec24"></a>

### 2.4. 使用步骤 [⌃](#top)

#### 2.4.1. 前置条件
在使用 CamFlow 前，请确认以下条件成立：

- **项目已本地部署**：已从github仓库克隆项目到本地；
- **同一局域网**：手机与 PC 端服务器处于同一 Wi-Fi/LAN；
- **PC 端服务已启动**：Sentinel PC 端服务对手机可达；
- **端口与防火墙放行**：默认端口为 `8000`（以你的 PC 端实际配置为准），PC 防火墙允许手机访问。

#### 2.4.2. 部署流程

1. **启动 PC 端 Sentinel 服务**；
2. 启动成功则能自动返回服务器IP地址`<PC_IP>:xxxx`；
3. 可通过在手机端浏览器访问 `http://<PC_IP>:xxxx/ping`，若返回 `OK` 字段则启动成功；
4. 手机与 PC 连接到 **同一 Wi-Fi**；
5. 打开 CamFlow ，等待一段时间，由程序自动寻找服务器；
6. 若成功则自动写入地址，与PC端建立联系；
7. 若失败则在弹出提示框中手动输入IP地址；
8. 观察 `Status` 是否变为 `Connected`；
9. 若连接成功，可点击主页面右上角进入设置页进行配置修改；
10. 打开 PC 端 Dashboard（进入返回的网址`http://<PC_IP>:xxxx/`）；
11. 点击 `Enable Ingest` 按钮，确认接收功能开启；
11. 观察到 Live View 窗口更新摄像端画面，则 CamFlow 成功正常运行。

---

<a id="sec3"></a>

## 3. 常见问题 [⌃](#top)

<details>
<summary><strong>无法自动发现服务器（Auto discover 失败）</strong></summary>

- 状态显示 `Discovering server...` 后失败；
- 弹出 “Could not find the server automatically”。

**可能原因**
1. 手机与 PC 不在同一局域网
2. 路由器启用 AP 隔离，导致设备间不可互访
3. 网络策略/设备系统限制 UDP 广播
4. PC 端服务未开启发现响应或端口被拦截

**排查步骤**
1. 在手机浏览器访问：`http://<PC_IP>:xxxx/ping`  
   - 能访问：说明 TCP 可达，转用手动输入即可  
   - 不能访问：检查防火墙/端口/网络隔离
2. 尝试手动输入 `PC_IP:xxxx` 并点击 `Test connection`

**解决方案**
- 使用“手动输入”作为稳定方案；
- 关闭路由器 AP 隔离；
- 在 PC 防火墙放行设定端口（以及发现所需 UDP 端口，如你实现使用的端口）。

</details>

---

<details>
<summary><strong>Test connection 失败（无法通过 /ping）</strong></summary>

- 设置页点击 Test connection 显示失败或无响应。

**可能原因**
1. 服务器地址填写错误（IP/端口）
2. PC 端服务未运行或监听端口不同
3. 防火墙阻止手机访问
4. 手机未连接 Wi-Fi

**排查步骤**
1. 确认手机 Wi-Fi 与 PC 网络一致
2. 在手机浏览器访问：`http://<PC_IP>:xxxx/ping`  
   - 能访问：说明 TCP 可达，转用手动输入即可  
   - 不能访问：检查防火墙/端口/网络隔离

**解决方案**
- 修正 IP/端口；
- 在 PC 防火墙放行设定端口（以及发现所需 UDP 端口，如你实现使用的端口）。

</details>

---

<details>
<summary><strong>CamFlow 显示已连接，但 Dashboard 无画面</strong></summary>

- 手机端状态正常；
- PC Dashboard 的 Live View 窗口不更新。

**可能原因**
1. PC Dashboard 未开启 ingest 功能（接收开关关闭）
2. 上传接口路径或字段名不匹配（例如服务端期望字段名与客户端不一致）
3. 上传成功但被服务端限流/丢弃（日志可见）
4. 浏览器缓存/页面未刷新导致显示滞后

**排查步骤**
1. 在 PC 端查看是否收到 `/upload` 请求
2. 刷新 Dashboard 页面，确认 ingest 开关状态
3. 降低发送压力：增大 Interval（例如 200~300ms）观察是否恢复

**解决方案**
- 确认开启 ingest 功能；
- 对齐服务端接口契约（路径、字段名、端口）；
- 调整发送间隔/分辨率/质量参数以适应网络与 PC 性能。

</details>

---

<details>
<summary><strong>安装 APK 提示不安全/无法安装</strong></summary>

- 系统提示“阻止安装未知来源应用”或“安装被拦截”。

**解决方案**
- 在系统设置中允许该来源安装；
- 确认 APK 安装包是来自 GitHub 项目 Releases 而非第三方转发。

</details>

---

<a id="sec4"></a>

## 4. 开发者文档 [⌃](#top)

对于二次开发者，该部分给出 CamFlow 在 Sentinel 系统中的结构位置、数据流路径与对外契约（API/协议），以支持后续扩展。

---

<a id="sec41"></a>

### 4.1. 实现框架 [⌃](#top)

```
CamFlow (Android App)
│
├─ [A] UI Layer（界面层）
│   │
│   ├─ Main Screen（主界面）
│   │   ├─ Camera Preview（实时预览）
│   │   ├─ Status Header
│   │   │   ├─ Status ∈ {NotConnected, Discovering, Connecting, Connected}
│   │   │   ├─ Server（当前服务器地址）
│   │   │   ├─ Mode ∈ {Normal}
│   │   │   └─ Interval（发送间隔 ms）
│   │   │
│   │   └─ Connection Dialog
│   │       └─ 自动发现失败 → 手动输入服务器地址
│   │
│   └─ Settings Screen（设置页）
│       ├─ Server Address Input
│       ├─ Auto Discover（UDP 广播发现）
│       ├─ Test Connection（/ping 测试）
│       ├─ Switches
│       │   ├─ Show Debug Info
│       │   ├─ Hide Camera Preview
│       │   └─ Stop Camera
│       └─ Save（保存配置）
│
├─ [B] Application State Layer（应用状态层）
│   │
│   ├─ Core State Variables
│   │   ├─ connectionState
│   │   ├─ serverUrl
│   │   ├─ uploadIntervalMs
│   │   └─ flags（debug / previewHidden / cameraStopped）
│   │
│   ├─ State Controller
│   │   ├─ UI ↔ 状态绑定
│   │   ├─ 状态驱动摄像头启动/停止
│   │   └─ 状态驱动上传线程启动/停止
│   │
│   └─ Thread Model
│       ├─ UI Thread
│       ├─ Camera Callback Thread
│       └─ Network Worker Thread
│
├─ [C] Camera Capture Pipeline（摄像头采集流水线）
│   │
│   ├─ Permission Management（CAMERA 权限）
│   │
│   ├─ Camera Provider（CameraX）
│   │   ├─ Preview UseCase（显示画面）
│   │   └─ ImageAnalysis UseCase（帧回调）
│   │
│   └─ Frame Dispatch Strategy
│       ├─ 最新帧覆盖策略（避免堆积）
│       └─ 丢帧机制（保障实时性）
│
├─ [D] Encoding & Upload Pipeline（编码与上传流水线）
│   │
│   ├─ Frame Encoder
│   │   ├─ YUV → RGB/BGR 转换
│   │   └─ JPEG 编码（quality 可调）
│   │
│   ├─ Rate Limiter
│   │   └─ 基于 intervalMs 的节流机制
│   │
│   ├─ HTTP Uploader
│   │   ├─ POST {serverUrl}/upload
│   │   ├─ multipart/form-data
│   │   └─ 响应处理（200 / 400 / 503）
│   │
│   └─ Error Handling
│       ├─ 连接失败 → 切换为 Error 状态
│       └─ UI 提示
│
├─ [E] Discovery & Connectivity Layer（发现与连通层）
│   │
│   ├─ UDP Auto Discovery
│   │   ├─ 发送 "FIND_PHONECAM_SERVER"
│   │   └─ 接收 "PHONECAM_SERVER http://ip:port"
│   │
│   ├─ Manual Address Input
│   │   └─ 支持 IP 或 IP:Port 输入
│   │
│   └─ Connectivity Check
│       └─ GET {serverUrl}/ping → 返回 "OK"
│
└─ [F] Persistence Layer（配置持久化）
    │
    ├─ SharedPreferences
    │   ├─ 保存 serverUrl
    │   ├─ 保存 switches 状态
    │   └─ 保存 intervalMs
    │
    └─ App Startup Restore
        ├─ 启动时恢复上次配置
        └─ 自动尝试连接（规划）
 ``` 

---

<a id="sec42"></a>

### 4.2. 开发 API 说明 [⌃](#top)

#### 4.2.1. 基础约定

- **Base URL**：`http://<PC_IP>:<PORT>`
- **默认端口**：由 PC 端启动参数决定（默认为 `8000`）
- **传输协议**：HTTP（明文，推荐仅在局域网内使用）
- **客户端上传字段名**：`image`

---

#### 4.2.2. 健康检查接口：`GET /ping`

- CamFlow Settings 页 “Test connection” 的可达性测试。
- 用于区分“网络不可用”还是“代码功能不可用”。

**请求**

- Method：`GET`
- Path：`/ping`
- Body：无

**响应格式**

- Status：`200 OK`
- Body：`OK`
- 超时、连接错误、或非 200 状态码，均视为测试失败。

**curl 示例**

```bash
curl -i "http://<PC_IP>:<PORT>/ping"
```
---

#### 4.2.3. 帧上传接口：`POST /upload`

- CamFlow 以“单帧 JPEG”的方式持续向服务器上传图像数据。
- 服务器端收到后会解码为图像帧并写入 `FrameBuffer`，供 `/stream` 与后续模块使用。

**请求**

- Method：`POST`
- Path：`/upload`
- Content-Type：`multipart/form-data`

| 字段名 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image` | JPEG bytes | 是 | 单帧 JPEG；服务端读取后解码为图像帧。|

> 说明：当前服务端仅强依赖 `image` 字段。

**响应格式**

- Status：`200 OK`
- Body：`OK`

| HTTP 状态码 | Body/含义 | 常见原因 |
|---:|---|---|
| 503 | `ingest disabled` | PC Dashboard 未开启 ingest（接收开关关闭） |
| 400 | `missing image` | 未带 `image` 字段（或字段名不匹配）|
| 400 | `decode failed` | 图片字节无法解码为图像（数据损坏/非 JPEG/编码异常 |
| 网络错误 | 超时/连接失败 | IP/端口错误、防火墙、Wi-Fi 不同网段 |

---

**curl 示例**

```bash
curl -i -X POST "http://<PC_IP>:<PORT>/upload" \
  -F "image=@frame.jpg;type=image/jpeg"
```

---

#### 4.2.4. 视频流接口：`GET /stream`

> 注意：该接口主要由 Sentinel Dashboard 使用，通过 `<img src="/stream">` 显示实时画面。CamFlow 通常不主动调用该接口。

---

**请求**

- Method：`GET`
- Path：`/stream`
- Body：无

---

**响应格式**

- Content-Type：`multipart/x-mixed-replace; boundary=frame`
- 数据形式：MJPEG 连续帧流

**curl 示例**

```bash
curl -v "http://<PC_IP>:<PORT>/stream" \
-I "http://<PC_IP>:<PORT>/stream"
```

---

#### 4.2.5. UDP 自动发现协议

CamFlow 支持在同一局域网内自动发现 Sentinel 服务器地址，以降低首次部署复杂度。

---

**协议参数**

- Transport：UDP
- Discovery Port：`37020`（服务器端监听端口）
- Server Bind：`0.0.0.0:37020`（监听所有网卡）

---

**客户端广播请求**

CamFlow 向局域网广播 UTF-8 文本报文：`FIND_PHONECAM_SERVER`

---

**服务器响应**

当服务器收到请求后，会向请求来源地址进行 UDP 单播回复（`sendto(..., addr)`），响应格式为：`PHONECAM_SERVER http://<PC_IP>:<PORT>`

其中：
- `<PORT>` 为服务器 HTTP 服务端口（即 CamFlow 后续用于访问 `/ping`、`/upload`、`/stream` 的端口）。
- `<PC_IP>` 由服务器根据请求来源 IP 推断得出：实现中通过 `_get_local_ip_for_peer(addr[0])` 选择与客户端同网段更可能可达的本机出口 IP，以降低多网卡场景下返回“不可达地址”的概率。

---

**协议交互流程**

```
CamFlow (Android)
    │
    │ UDP Broadcast to 255.255.255.255:37020
    │ Payload: "FIND_PHONECAM_SERVER"
    ▼
Sentinel PC (UDP listener on port 37020)
    │
    │ UDP Unicast Response to sender
    │ Payload: "PHONECAM_SERVER http://<IP>:<PORT>"
    ▼
CamFlow
    │
    │ Parse Base URL
    │ → Execute GET /ping
    │ → If OK, start POST /upload loop
--------
```
---

<a id="sec5"></a>

## 5. 版本信息与项目说明 [⌃](#top)

<a id="sec51"></a>

### 5.1. 系统版本信息 [⌃](#top)

本系统由 PC 端服务器程序与 Android 端 CamFlow 应用组成，版本信息如下：
- CamFlow（Android）版本：v1.0.0-beta
- 本文档版本：v1.0.0
- 最后更新日期：2026-02-23

---

<a id="sec52"></a>

### 5.2. 测试环境说明 [⌃](#top)

本系统在以下环境中完成测试：

### Android 端

- 软件环境：Android 10 及以上版本
- 测试设备：nova 8 SE 活力版 - HarmonyOS 3.0.0 
- 网络环境：同一局域网 Wi-Fi

### PC 端

- 软件环境：Windows 10 / Windows 11
- Python 版本：Python 3.9+
- 依赖库：Flask、OpenCV、Requests 等
- 网络环境：局域网（LAN）

> 不建议在公网环境直接暴露接口，尚未增加安全认证机制。

---

<a id="sec53"></a>

## 5.3. 后续规划 [⌃](#top)

为提升系统完整性与可扩展性，可做的优化包括：

- Token / API Key 认证机制（如需接触公网）
- WebSocket 长连接替代当前的 HTTP 轮询（降低延迟和损耗）
- 自适应帧率/分辨率控制（根据网络情况动态调整 interval）
- 后台运行模式（屏幕关闭仍持续上传）
- 本地缓存队列（弱网缓冲）

---

<a id="sec54"></a>

## 5.4. 使用与授权说明 [⌃](#top)

© 2026 Suzuran0y

Sentinel 项目基于 MIT License 开源发布。

本项目用于学习、研究与技术验证目的。请在使用前确保符合当地法律法规与场景授权要求。

如需在现实生产环境或商业场景使用，请自行完善安全机制与性能优化。
