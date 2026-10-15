<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Circle, CircleCheck, CircleX, LoaderCircle } from '@lucide/vue'
import { ESPLoader, Transport } from 'esptool-js'
// spark-md5 does not publish its own TypeScript declarations.
// @ts-expect-error -- CommonJS package without declaration files.
import SparkMD5 from 'spark-md5'
import { withBase } from 'vitepress'
import { VPButton } from 'vitepress/theme'

type SerialPortHandle = ConstructorParameters<typeof Transport>[0]
type SerialPortInfo = { usbVendorId?: number; usbProductId?: number }
type FirmwareChoice = 'justread' | 'factory'
type FirmwareAsset = { label: string; url: string; bytes: number; sha256?: string }
type ResourceAsset = FirmwareAsset & { blockBytes: number }
type FirmwareManifest = {
  schemaVersion: number
  target: string
  flashBytes: number
  firmwares: Record<FirmwareChoice, FirmwareAsset>
  resources: { systemFont: ResourceAsset }
}
type FlashState =
  | 'start' | 'ready' | 'flashing' | 'complete' | 'error'
  | 'resources' | 'resource_importing' | 'resource_complete' | 'resource_error'
type BrowserSerialPort = SerialPortHandle & {
  open(options: { baudRate: number }): Promise<void>
  close(): Promise<void>
  readable: ReadableStream<Uint8Array> | null
  writable: WritableStream<Uint8Array> | null
  setSignals?(signals: { dataTerminalReady?: boolean; requestToSend?: boolean }): Promise<void>
}
type SerialApi = {
  requestPort(options: { filters: Array<{ usbVendorId: number; usbProductId: number }> }): Promise<SerialPortHandle>
}

const FLASH_BYTES = 16 * 1024 * 1024
const JUSTREAD_PROJECT = 'Read_Pico'
const deviceFilters = [{ usbVendorId: 0x303a, usbProductId: 0x1001 }]
const devices = [{ id: 'pico-esp32-s3', label: '小纸 Pico · ESP32-S3' }]
const flashSteps = ['下载并校验固件', '连接设备', '安装固件', '验证安装结果', '重置设备']

const selectedDevice = ref<SerialPortHandle | null>(null)
const selectedModel = ref(devices[0].id)
const selectedVersion = ref<FirmwareChoice | 'custom'>('justread')
const customFirmwareFile = ref<File | null>(null)
const errorMessage = ref('')
const connecting = ref(false)
const isBusy = ref(false)
const flashState = ref<FlashState>('start')
const activeStepIndex = ref(0)
const progress = ref(0)
const status = ref('')
const completedFirmwareName = ref('')
const pendingFirmwareName = ref('')
const confirmDialog = ref<HTMLDialogElement | null>(null)
const manifest = ref<FirmwareManifest | null>(null)
const manifestLoading = ref(true)
const manifestError = ref('')
const resourceProgress = ref(0)
const resourceStatus = ref('')
const resourceError = ref('')
const resourceResult = ref<'installed' | 'already' | 'not-needed' | ''>('')
let resolveFlashConfirmation: ((confirmed: boolean) => void) | null = null
let activeTransport: Transport | null = null

const firmwareVersions = computed(() => [
  { id: 'justread', label: manifest.value?.firmwares.justread.label ?? 'JustRead · 小纸 Pico' },
  { id: 'factory', label: manifest.value?.firmwares.factory.label ?? 'MindReset 原厂固件' },
])
const firmwareName = computed(() => selectedVersion.value === 'custom'
  ? '自定义 · ' + (customFirmwareFile.value?.name ?? '未选择文件')
  : firmwareVersions.value.find(({ id }) => id === selectedVersion.value)!.label)
const canFlash = computed(() => selectedVersion.value === 'custom'
  ? Boolean(customFirmwareFile.value)
  : Boolean(manifest.value?.firmwares[selectedVersion.value]))
const resourceCompletionText = computed(() => {
  if (resourceResult.value === 'already') return '设备已有有效系统字体，请继续在设备屏幕完成首次启动引导。'
  if (resourceResult.value === 'not-needed') return '设备当前不需要导入首次启动资源。'
  return '系统字体已写入设备 SD 卡。请在设备屏幕上选择登录或注册云账户，或暂不使用并进入书架。'
})

onMounted(() => { void loadManifest() })
onBeforeUnmount(() => { settleFlashConfirmation(false) })

async function loadManifest() {
  manifestLoading.value = true
  manifestError.value = ''
  try {
    const response = await fetch(withBase('/firmware.json'), { cache: 'no-store' })
    if (!response.ok) throw new Error('固件配置加载失败。')
    const data = await response.json() as FirmwareManifest
    const font = data.resources?.systemFont
    if (
      data.schemaVersion !== 1 || data.target !== 'ESP32-S3' || data.flashBytes !== FLASH_BYTES
      || !data.firmwares?.justread?.url || data.firmwares.justread.bytes !== FLASH_BYTES
      || !data.firmwares?.factory?.url || data.firmwares.factory.bytes !== FLASH_BYTES
      || !font?.url || !Number.isSafeInteger(font.bytes) || font.bytes <= 0
      || !Number.isSafeInteger(font.blockBytes) || font.blockBytes <= 0
    ) throw new Error('固件配置格式无效。')
    manifest.value = data
  } catch (error) {
    manifestError.value = error instanceof Error ? error.message : '固件配置加载失败。'
  } finally {
    manifestLoading.value = false
  }
}

function getSerialApi() {
  return (navigator as Navigator & { serial?: SerialApi }).serial
}

async function connectDevice() {
  if (connecting.value || isBusy.value) return
  errorMessage.value = ''
  const serial = getSerialApi()
  if (!window.isSecureContext || !serial) {
    errorMessage.value = '请使用 HTTPS 下的 Chrome 或 Edge。'
    return
  }
  connecting.value = true
  try {
    const port = await serial.requestPort({ filters: deviceFilters })
    const info = (port as SerialPortHandle & { getInfo: () => SerialPortInfo }).getInfo()
    if (info.usbVendorId !== 0x303a || info.usbProductId !== 0x1001) {
      throw new Error('请选择通过 USB 连接的小纸 Pico。')
    }
    selectedDevice.value = port
    flashState.value = 'ready'
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'NotFoundError')) {
      errorMessage.value = error instanceof Error ? error.message : '无法选择设备，请检查 USB 连接后重试。'
    }
  } finally {
    connecting.value = false
  }
}

function chooseCustomFirmware(event: Event) {
  if (isBusy.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size !== FLASH_BYTES) {
    customFirmwareFile.value = null
    selectedVersion.value = 'justread'
    input.value = ''
    errorMessage.value = '自定义固件须为 16 MiB 整片镜像。'
    return
  }
  errorMessage.value = ''
  customFirmwareFile.value = file
  selectedVersion.value = 'custom'
}

function sha256(data: Uint8Array) {
  return crypto.subtle.digest('SHA-256', data).then((digest) =>
    Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join(''),
  )
}

function md5(data: Uint8Array) {
  return SparkMD5.ArrayBuffer.hash(data.buffer)
}

function isEsp32S3Image(data: Uint8Array, offset = 0) {
  return data[offset] === 0xe9 && data[offset + 12] === 0x09 && data[offset + 13] === 0x00
}

function appProjectName(data: Uint8Array, offset: number) {
  const descriptorOffset = offset + 0x20
  if (data.length < descriptorOffset + 256 || !isEsp32S3Image(data, offset)) return ''
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength)
  if (view.getUint32(descriptorOffset, true) !== 0xabcd5432) return ''
  let end = descriptorOffset + 48
  while (end < descriptorOffset + 80 && data[end] !== 0) end++
  return new TextDecoder().decode(data.subarray(descriptorOffset + 48, end))
}

function validateFullImage(data: Uint8Array, choice: FirmwareChoice | 'custom') {
  if (data.byteLength !== FLASH_BYTES) throw new Error('全量镜像大小必须为 16 MiB。')
  if (!isEsp32S3Image(data) || data[0x8000] !== 0xaa || data[0x8001] !== 0x50 || !isEsp32S3Image(data, 0x10000)) {
    throw new Error('镜像不是小纸 Pico ESP32-S3 的 16 MiB 全量镜像。')
  }
  if (choice === 'justread' && appProjectName(data, 0x10000) !== JUSTREAD_PROJECT) {
    throw new Error('所选镜像不是 JustRead 固件。')
  }
}

async function fetchVerifiedAsset(asset: FirmwareAsset, label: string) {
  const url = asset.url.startsWith('/') && !asset.url.startsWith('//') ? withBase(asset.url) : asset.url
  const response = await fetch(url, { cache: 'no-store' })
  if (!response.ok) throw new Error(label + '下载失败。')
  const data = new Uint8Array(await response.arrayBuffer())
  if (data.byteLength !== asset.bytes) throw new Error(label + '文件大小校验失败。')
  if (asset.sha256?.trim() && await sha256(data) !== asset.sha256.trim().toLowerCase()) {
    throw new Error(label + ' SHA-256 校验失败。')
  }
  return data
}

async function loadFirmware(choice: FirmwareChoice | 'custom') {
  if (choice === 'custom') {
    const file = customFirmwareFile.value
    if (!file) throw new Error('请选择固件文件。')
    const data = new Uint8Array(await file.arrayBuffer())
    validateFullImage(data, choice)
    return { data, isJustRead: appProjectName(data, 0x10000) === JUSTREAD_PROJECT }
  }
  if (!manifest.value) throw new Error(manifestError.value || '固件配置尚未就绪。')
  const asset = manifest.value.firmwares[choice]
  const data = await fetchVerifiedAsset(asset, asset.label)
  validateFullImage(data, choice)
  return { data, isJustRead: choice === 'justread' }
}

function confirmFullFlashWrite() {
  return new Promise<boolean>((resolve) => {
    const dialog = confirmDialog.value
    if (!dialog) return resolve(false)
    resolveFlashConfirmation = resolve
    dialog.showModal()
  })
}

function settleFlashConfirmation(confirmed: boolean) {
  resolveFlashConfirmation?.(confirmed)
  resolveFlashConfirmation = null
  confirmDialog.value?.close()
}

async function startFlashing() {
  const port = selectedDevice.value
  if (isBusy.value || connecting.value || !port || !canFlash.value) return
  const targetFirmware = selectedVersion.value
  pendingFirmwareName.value = firmwareName.value
  const targetFirmwareName = pendingFirmwareName.value
  isBusy.value = true
  try {
    if (!(await confirmFullFlashWrite())) return
    flashState.value = 'flashing'
    errorMessage.value = ''
    completedFirmwareName.value = ''
    activeStepIndex.value = 0
    progress.value = 0
    status.value = '获取并校验 16 MiB 固件…'
    const firmware = await loadFirmware(targetFirmware)
    activeStepIndex.value = 1
    status.value = '连接 ESP32-S3…'
    const terminal = { clean() {}, writeLine(_data: string) {}, write(_data: string) {} }
    activeTransport = new Transport(port, false)
    const loader = new ESPLoader({ transport: activeTransport, baudrate: 460800, romBaudrate: 115200, terminal })
    const chipName = await loader.main()
    if (!chipName.includes('ESP32-S3')) throw new Error('检测到的不是 ESP32-S3，未写入设备。')
    if (await loader.detectFlashSize() !== '16MB') throw new Error('设备 Flash 容量不是 16 MiB，未写入设备。')

    activeStepIndex.value = 2
    status.value = '写入 16 MiB 镜像…'
    await loader.writeFlash({
      fileArray: [{ data: firmware.data, address: 0 }],
      flashMode: 'keep', flashFreq: 'keep', flashSize: 'keep',
      eraseAll: false, compress: true,
      reportProgress: (_fileIndex, written, total) => {
        progress.value = total ? Math.min(100, Math.floor((written / total) * 100)) : 0
      },
    })
    activeStepIndex.value = 3
    progress.value = 0
    status.value = '校验整片 Flash…'
    if (await loader.flashMd5sum(0, FLASH_BYTES) !== md5(firmware.data)) {
      throw new Error('整片写入校验失败，请保持 USB 连接并重试。')
    }
    activeStepIndex.value = 4
    status.value = '复位设备…'
    await loader.after('custom_reset', false, 'R1|W100|R0')
    activeStepIndex.value = flashSteps.length
    progress.value = 100
    completedFirmwareName.value = targetFirmwareName
    if (firmware.isJustRead) {
      resourceStatus.value = '固件已刷写完成。请重新连接设备并导入首次启动资源。'
      flashState.value = 'resources'
    } else {
      flashState.value = 'complete'
    }
    status.value = targetFirmwareName + '刷写完成。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '刷写失败，请保持 USB 连接并重试。'
    flashState.value = 'error'
    status.value = ''
  } finally {
    try { await activeTransport?.disconnect() } catch { /* USB may disconnect after reset. */ }
    if (activeTransport) selectedDevice.value = null
    activeTransport = null
    isBusy.value = false
  }
}

function returnToSelection() {
  if (isBusy.value) return
  errorMessage.value = ''
  flashState.value = selectedDevice.value ? 'ready' : 'start'
  activeStepIndex.value = 0
  progress.value = 0
  status.value = ''
  completedFirmwareName.value = ''
  resourceStatus.value = ''
  resourceError.value = ''
  resourceProgress.value = 0
  resourceResult.value = ''
}

function openResourceImport() {
  if (isBusy.value || connecting.value) return
  selectedDevice.value = null
  flashState.value = 'resources'
  resourceStatus.value = ''
  resourceError.value = ''
  resourceProgress.value = 0
  resourceResult.value = ''
}

type SerialLineReader = {
  waitFor(match: (line: string) => boolean, timeoutMs: number): Promise<string>
  stop(): Promise<void>
}

function readSerialLines(stream: ReadableStream<Uint8Array>): SerialLineReader {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  const queued: string[] = []
  const waiters: Array<{
    match: (line: string) => boolean
    resolve: (line: string) => void
    reject: (error: Error) => void
    timer: ReturnType<typeof setTimeout>
  }> = []
  let buffer = ''
  let stopped = false

  const rejectWaiters = (error: Error) => {
    for (const waiter of waiters.splice(0)) {
      clearTimeout(waiter.timer)
      waiter.reject(error)
    }
  }

  const dispatch = (line: string) => {
    for (let index = waiters.length - 1; index >= 0; index--) {
      const waiter = waiters[index]
      if (waiter.match(line)) {
        waiters.splice(index, 1)
        clearTimeout(waiter.timer)
        waiter.resolve(line)
        return
      }
    }
    queued.push(line)
    if (queued.length > 500) queued.shift()
  }

  const pump = (async () => {
    try {
      while (!stopped) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split(/\r?\n/)
        buffer = parts.pop() ?? ''
        for (const line of parts) dispatch(line)
      }
      rejectWaiters(new Error('设备串口已关闭。'))
    } catch (error) {
      rejectWaiters(error instanceof Error ? error : new Error('设备串口读取失败。'))
    } finally {
      try { reader.releaseLock() } catch { /* stream already released */ }
    }
  })()

  return {
    waitFor(match, timeoutMs) {
      const foundIndex = queued.findIndex(match)
      if (foundIndex >= 0) return Promise.resolve(queued.splice(foundIndex, 1)[0])
      if (stopped) return Promise.reject(new Error('设备串口已关闭。'))
      return new Promise((resolve, reject) => {
        const waiter = {
          match,
          resolve,
          reject,
          timer: setTimeout(() => {
            const index = waiters.indexOf(waiter)
            if (index >= 0) waiters.splice(index, 1)
            reject(new Error('等待设备响应超时，请检查 USB 连接后重试。'))
          }, timeoutMs),
        }
        waiters.push(waiter)
      })
    },
    async stop() {
      stopped = true
      try { await reader.cancel() } catch { /* device may already be disconnected */ }
      await pump.catch(() => undefined)
    },
  }
}

function responseWaiter(match: (line: string) => boolean) {
  return (line: string) => line.includes('JR_UPLOAD_ERROR') || match(line)
}

async function sendCommand(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  lines: SerialLineReader,
  command: string,
  match: (line: string) => boolean,
  timeoutMs = 15000,
) {
  await writer.write(new TextEncoder().encode(command + '\n'))
  const line = await lines.waitFor(responseWaiter(match), timeoutMs)
  if (line.includes('JR_UPLOAD_ERROR')) throw new Error('设备拒绝资源导入：' + line)
  return line
}

function parseResourceStatus(line: string) {
  return Object.fromEntries(
    Array.from(line.matchAll(/(phase|first|required|valid|busy|error|done|total)=(-?\d+)/g), ([, key, value]) => [key, Number(value)]),
  ) as Record<string, number>
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function startResourceImport() {
  if (isBusy.value || !manifest.value) return
  const serial = getSerialApi()
  if (!window.isSecureContext || !serial) {
    flashState.value = 'resource_error'
    resourceError.value = '请使用 HTTPS 下的 Chrome 或 Edge。'
    return
  }

  // requestPort must be called directly from this button gesture.
  const portPromise = serial.requestPort({ filters: deviceFilters })
  isBusy.value = true
  flashState.value = 'resource_importing'
  resourceStatus.value = '连接设备…'
  resourceError.value = ''
  resourceProgress.value = 0
  resourceResult.value = ''

  let port: BrowserSerialPort | null = null
  let writer: WritableStreamDefaultWriter<Uint8Array> | null = null
  let lines: SerialLineReader | null = null
  try {
    port = await portPromise as BrowserSerialPort
    const info = (port as SerialPortHandle & { getInfo: () => { usbVendorId?: number; usbProductId?: number } }).getInfo()
    if (info.usbVendorId !== 0x303a || info.usbProductId !== 0x1001) {
      throw new Error('请选择通过 USB 连接的小纸 Pico。')
    }
    await port.open({ baudRate: 115200 })
    await port.setSignals?.({ dataTerminalReady: false, requestToSend: false })
    if (!port.readable || !port.writable) throw new Error('设备串口不可读写。')
    lines = readSerialLines(port.readable)
    writer = port.writable.getWriter()

    const getStatus = async () => {
      const line = await sendCommand(writer!, lines!, 'jr resources status', (text) => text.includes('JR_RESOURCE_STATUS:'), 15000)
      return parseResourceStatus(line)
    }
    resourceStatus.value = '检查设备资源状态…'
    let deviceStatus = await getStatus()
    const statusDeadline = Date.now() + 120000
    while (deviceStatus.busy === 1) {
      if (Date.now() > statusDeadline) throw new Error('设备资源检查超时，请稍后重试。')
      await wait(500)
      deviceStatus = await getStatus()
    }

    if (deviceStatus.valid === 1) {
      resourceResult.value = 'already'
      flashState.value = 'resource_complete'
      return
    }
    if (deviceStatus.required !== 1) {
      resourceResult.value = 'not-needed'
      flashState.value = 'resource_complete'
      return
    }
    if (deviceStatus.phase === 1) {
      throw new Error('设备尚未检测到 SD 卡。插入 SD 卡后，在设备上点“重新检查”，再重新导入。')
    }
    while (deviceStatus.phase !== 2 && deviceStatus.phase !== 7) {
      if (Date.now() > statusDeadline) throw new Error('等待设备检查 SD 卡超时。')
      await wait(500)
      deviceStatus = await getStatus()
      if (deviceStatus.valid === 1 || deviceStatus.required !== 1) {
        resourceResult.value = deviceStatus.valid === 1 ? 'already' : 'not-needed'
        flashState.value = 'resource_complete'
        return
      }
      if (deviceStatus.phase === 1) {
        throw new Error('设备尚未检测到 SD 卡。插入 SD 卡后，在设备上点“重新检查”，再重新导入。')
      }
    }

    const font = manifest.value.resources.systemFont
    resourceStatus.value = '下载系统字体…'
    const fontData = await fetchVerifiedAsset(font, font.label)
    // The device requires its pinned resource digest even when development JSON omits one.
    const fontDigest = font.sha256?.trim() || await sha256(fontData)
    resourceStatus.value = '开始向设备发送系统字体…'
    await sendCommand(writer, lines, 'jr resources begin ' + font.bytes + ' ' + fontDigest + ' ' + font.blockBytes, (text) => text.includes('JR_UPLOAD_BEGIN:'), 30000)

    for (let offset = 0; offset < fontData.byteLength; offset += font.blockBytes) {
      const end = Math.min(fontData.byteLength, offset + font.blockBytes)
      await writer.write(fontData.subarray(offset, end))
      const sent = end
      const ack = await lines.waitFor(
        responseWaiter((text) => text.includes('JR_UPLOAD_ACK: bytes=' + sent)),
        30000,
      )
      if (ack.includes('JR_UPLOAD_ERROR')) throw new Error('设备写入失败：' + ack)
      resourceProgress.value = Math.floor((sent / fontData.byteLength) * 100)
      resourceStatus.value = '写入系统字体 ' + resourceProgress.value + '%'
    }

    resourceStatus.value = '设备正在校验并保存系统字体…'
    const done = await lines.waitFor(responseWaiter((text) => text.includes('JR_UPLOAD_DONE:')), 180000)
    if (done.includes('JR_UPLOAD_ERROR')) throw new Error('设备资源写入失败：' + done)
    resourceProgress.value = 100
    resourceResult.value = 'installed'
    flashState.value = 'resource_complete'
    resourceStatus.value = '资源已写入。'
  } catch (error) {
    flashState.value = 'resource_error'
    resourceError.value = error instanceof Error ? error.message : '资源导入失败，请保持 USB 连接后重试。'
  } finally {
    try { await lines?.stop() } catch { /* device may have reset */ }
    try { writer?.releaseLock() } catch { /* stream may have closed */ }
    if (port) {
      try { await port.close() } catch { /* already closed */ }
    }
    isBusy.value = false
  }
}
</script>

<template>
  <main class="flash-page">
    <h1>在线刷机</h1>
    <section class="flash-panel" aria-live="polite" aria-atomic="true">
      <div
        v-if="flashState === 'resources' || flashState === 'resource_importing' || flashState === 'resource_complete' || flashState === 'resource_error'"
        class="selection-form"
      >
        <p class="flash-status">{{ flashState === 'resource_complete' ? '首次启动资源已就绪' : '导入首次启动资源' }}</p>
        <p v-if="flashState === 'resource_complete'">{{ resourceCompletionText }}</p>
        <template v-else>
          <p>首次启动需要系统字体。请插入设备 SD 卡并通过 USB 连接设备。</p>
          <VPButton
            :text="isBusy ? '正在导入…' : '通过 USB 导入资源'"
            size="big"
            :disabled="isBusy || !manifest"
            @click="startResourceImport"
          />
        </template>
        <div v-if="resourceStatus" class="step-row">
          <LoaderCircle v-if="isBusy" class="step-icon spinning" aria-hidden="true" />
          <CircleCheck v-else-if="flashState === 'resource_complete'" class="step-icon" aria-hidden="true" />
          <Circle v-else class="step-icon" aria-hidden="true" />
          <span>{{ resourceStatus }}</span>
          <span v-if="flashState === 'resource_importing' && resourceProgress > 0" class="step-percent">{{ resourceProgress }}%</span>
        </div>
        <div v-if="flashState === 'resource_importing' && resourceProgress > 0" class="progress-track" role="progressbar" :aria-valuenow="resourceProgress" aria-valuemin="0" aria-valuemax="100" aria-label="系统字体导入">
          <div class="progress-value" :style="{ width: `${resourceProgress}%` }" />
        </div>
        <p v-if="resourceError" class="connection-error" role="alert">{{ resourceError }}</p>
        <VPButton text="返回设备选择" theme="alt" :disabled="isBusy" @click="returnToSelection" />
      </div>
      <div v-else-if="flashState === 'flashing' || flashState === 'complete' || flashState === 'error'" class="flash-progress">
        <p class="flash-status">{{ flashState === 'complete' ? '刷机完成' : flashState === 'error' ? '刷写失败' : '正在烧录' + pendingFirmwareName + '…' }}</p>
        <p v-if="status">{{ status }}</p>
        <ol class="flash-steps">
          <li
            v-for="(step, index) in flashSteps"
            :key="step"
            class="flash-step"
            :class="{
              'is-complete': index < activeStepIndex || flashState === 'complete',
              'is-active': index === activeStepIndex && flashState !== 'complete',
              'is-error': index === activeStepIndex && flashState === 'error',
            }"
          >
            <div class="step-row">
              <CircleCheck v-if="index < activeStepIndex || flashState === 'complete'" class="step-icon" aria-hidden="true" />
              <CircleX v-else-if="index === activeStepIndex && flashState === 'error'" class="step-icon" aria-hidden="true" />
              <LoaderCircle v-else-if="index === activeStepIndex && flashState === 'flashing'" class="step-icon spinning" aria-hidden="true" />
              <Circle v-else class="step-icon" aria-hidden="true" />
              <span>{{ step }}</span>
              <span v-if="index === activeStepIndex && (index === 2 || index === 3) && flashState === 'flashing'" class="step-percent">
                {{ progress }}%
              </span>
            </div>
            <div v-if="index === activeStepIndex && (index === 2 || index === 3) && flashState === 'flashing'" class="progress-track" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100" :aria-label="step">
              <div class="progress-value" :style="{ width: `${progress}%` }" />
            </div>
          </li>
        </ol>
        <p v-if="flashState === 'error'" class="connection-error" role="alert">{{ errorMessage }}</p>
        <VPButton v-if="flashState === 'error'" text="返回设备选择" theme="alt" @click="returnToSelection" />
        <VPButton v-if="flashState === 'complete'" text="返回" theme="alt" @click="returnToSelection" />
      </div>

      <div v-else class="selection-form">
        <label class="field-label" for="device-model">设备</label>
        <select id="device-model" v-model="selectedModel" :disabled="isBusy || connecting">
          <option v-for="device in devices" :key="device.id" :value="device.id">
            {{ device.label }}
          </option>
        </select>

        <label class="field-label" for="firmware-version">版本</label>
        <select
          id="firmware-version"
          v-model="selectedVersion"
          :disabled="isBusy || connecting || manifestLoading"
        >
          <option v-for="version in firmwareVersions" :key="version.id" :value="version.id">
            {{ version.label }}
          </option>
          <option v-if="customFirmwareFile" value="custom">
            自定义 · {{ customFirmwareFile.name }}
          </option>
        </select>

        <input
          id="custom-firmware"
          class="visually-hidden"
          type="file"
          accept=".bin,application/octet-stream"
          :disabled="isBusy || connecting"
          @change="chooseCustomFirmware"
        />
        <label class="custom-file-link" for="custom-firmware">
          {{ customFirmwareFile ? '更换自定义固件' : '选择自定义固件' }}
        </label>
        <VPButton
          :text="isBusy ? '等待确认…' : connecting ? '正在连接…' : selectedDevice ? '开始刷机' : '连接设备'"
          size="big"
          :disabled="isBusy || connecting || !canFlash"
          @click="selectedDevice ? startFlashing() : connectDevice()"
        />
        <VPButton text="资源导入" theme="alt" :disabled="isBusy || connecting || !manifest" @click="openResourceImport" />
        <p v-if="manifestLoading">正在读取固件配置…</p>
        <p v-if="manifestError" class="connection-error" role="alert">{{ manifestError }}</p>
        <VPButton v-if="manifestError" text="重新加载固件配置" theme="alt" :disabled="isBusy || manifestLoading" @click="loadManifest" />
        <p v-if="errorMessage" class="connection-error" role="alert">{{ errorMessage }}</p>
      </div>
    </section>

    <dialog
      ref="confirmDialog"
      class="flash-confirm-dialog"
      aria-labelledby="flash-confirm-title"
      aria-describedby="flash-confirm-description"
      @cancel.prevent="settleFlashConfirmation(false)"
      @click.self="settleFlashConfirmation(false)"
    >
      <h2 id="flash-confirm-title" class="flash-confirm-title">确认刷写 {{ pendingFirmwareName }}</h2>
      <p id="flash-confirm-description" class="flash-confirm-description">
        这会将固件写入整片 16 MiB Flash，并覆盖设备中的现有固件、设置和数据。
      </p>
      <div class="dialog-actions">
        <VPButton text="取消" theme="alt" @click="settleFlashConfirmation(false)" />
        <VPButton text="确定" @click="settleFlashConfirmation(true)" />
      </div>
    </dialog>
  </main>
</template>

<style scoped>
.flash-page {
  box-sizing: border-box;
  display: grid;
  width: 100%;
  margin-inline: auto;
  align-content: start;
  justify-items: center;
  padding: max(2rem, env(safe-area-inset-top))
    max(1.5rem, env(safe-area-inset-right))
    max(2rem, env(safe-area-inset-bottom))
    max(1.5rem, env(safe-area-inset-left));
}

.flash-panel {
  box-sizing: border-box;
  display: grid;
  width: min(100%, 28rem);
  gap: 1.25rem;
  padding: 2rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 18px;
  background: var(--vp-c-bg);
  box-shadow: var(--vp-shadow-1);
  text-align: left;
}

.flash-page > h1 {
  border: 0;
}

.flash-confirm-dialog {
  box-sizing: border-box;
  width: min(calc(100% - 2rem), 32rem);
  padding: 1rem;
  border: 0;
  border-radius: 12px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  box-shadow: var(--vp-shadow-3);
}

.flash-confirm-dialog::backdrop {
  background: rgb(0 0 0 / 55%);
}

.flash-confirm-dialog #flash-confirm-title {
  margin: 0;
  border: 0;
  padding: 0;
  font: inherit;
  font-weight: 600;
  line-height: 1.4;
}

.flash-confirm-dialog #flash-confirm-description {
  margin: 0.5rem 0 0.75rem;
  padding: 0;
  color: var(--vp-c-text-2);
  font: inherit;
  line-height: 1.6;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.selection-form {
  display: grid;
  gap: 0.625rem;
}

.selection-form select {
  width: 100%;
  min-height: 2.5rem;
  border-radius: 10px;
  padding: 0.25rem 1rem;
  appearance: auto;
  -webkit-appearance: menulist;
}

.field-label {
  color: var(--vp-c-text-2);
  font-weight: 600;
}

.custom-file-link {
  justify-self: center;
  color: var(--vp-c-brand-1);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.custom-file-link:hover {
  color: var(--vp-c-brand-2);
}

.custom-file-link:focus-within,
.visually-hidden:focus-visible + .custom-file-link {
  outline: 2px solid var(--vp-c-brand-1);
  outline-offset: 3px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.flash-status {
  margin: 0 0 1rem;
  border: 0;
  padding: 0;
  color: var(--vp-c-text-1);
  font-weight: 600;
  line-height: 1.35;
  text-align: center;
}

.flash-steps {
  margin: 0;
  padding: 0;
  list-style: none;
}

.flash-step {
  padding: 1rem 0;
  color: var(--vp-c-text-3);
}

.flash-step.is-complete {
  color: var(--vp-c-text-2);
}

.flash-step.is-active {
  color: var(--vp-c-text-1);
}

.flash-step.is-error {
  color: var(--vp-c-danger-1);
}

.step-row {
  display: grid;
  grid-template-columns: 1.5rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.75rem;
}

.step-icon {
  width: 1.375rem;
  height: 1.375rem;
  color: var(--vp-c-text-3);
}

.is-complete .step-icon {
  color: var(--vp-c-brand-1);
}

.is-active .step-icon {
  color: var(--vp-c-brand-1);
}

.is-error .step-icon {
  color: var(--vp-c-danger-1);
}

.step-percent {
  color: var(--vp-c-text-2);
  font-variant-numeric: tabular-nums;
}

.progress-track {
  height: 0.375rem;
  margin: 0.75rem 0 0 2.125rem;
  overflow: hidden;
  border-radius: 999px;
  background: var(--vp-c-bg-soft);
}

.progress-value {
  height: 100%;
  border-radius: inherit;
  background: var(--vp-c-brand-1);
  transition: width 150ms ease;
}

.connection-error {
  max-width: 28rem;
  margin: 0;
  color: var(--vp-c-danger-1);
}

.spinning {
  animation: spin 1s linear infinite;
}

@media (max-width: 480px) {
  .flash-panel {
    padding: 1.4rem;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinning {
    animation-duration: 2s;
  }

  .progress-value {
    transition: none;
  }
}
</style>
