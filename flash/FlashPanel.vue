<script setup lang="ts">
import { ref } from 'vue'
import { Circle, CircleCheck, CircleX, LoaderCircle } from '@lucide/vue'
import { ESPLoader, Transport } from 'esptool-js'
// spark-md5 does not publish its own TypeScript declarations.
// @ts-expect-error -- CommonJS package without declaration files.
import SparkMD5 from 'spark-md5'
import { VPButton } from 'vitepress/theme'

type SerialPortHandle = ConstructorParameters<typeof Transport>[0]
type SerialPortInfo = {
  usbVendorId?: number
  usbProductId?: number
}
type FirmwareVersion = {
  id: string
  label: string
  url: string
  sha256: string
  size: number
}
type FlashState = 'start' | 'ready' | 'flashing' | 'complete' | 'error'

const FLASH_SIZE = 16 * 1024 * 1024
const FACTORY_FIRMWARE: FirmwareVersion = {
  id: 'mindreset-factory',
  label: 'MindReset 原厂固件',
  url: 'https://assets.crossmux.cn/firmware/builds/readpico-factory/28cde682a4468a581c278761922724f57d976418/readpico-factory.bin',
  sha256: '3dda5bfa22b8dbd27d411b960e6153c184a9c2fca7d97ad0bc8a5c7ac219a719',
  size: FLASH_SIZE,
}
const devices = [{ id: 'pico-esp32-s3', label: '小纸 Pico · ESP32-S3' }]
const firmwareVersions = [FACTORY_FIRMWARE]
const flashSteps = ['下载并校验固件', '连接设备', '安装固件', '验证安装结果', '重置设备']

const selectedDevice = ref<SerialPortHandle | null>(null)
const selectedModel = ref(devices[0].id)
const selectedVersion = ref(FACTORY_FIRMWARE.id)
const customFirmwareFile = ref<File | null>(null)
const errorMessage = ref('')
const connecting = ref(false)
const flashState = ref<FlashState>('start')
const activeStepIndex = ref(0)
const progress = ref(0)
const confirmDialog = ref<HTMLDialogElement | null>(null)
let resolveFlashConfirmation: ((confirmed: boolean) => void) | null = null
let activeTransport: Transport | null = null

function setFlashError(message: string) {
  errorMessage.value = message
  flashState.value = 'error'
}

async function connectDevice() {
  errorMessage.value = ''

  const serial = (navigator as Navigator & {
    serial?: {
      requestPort: (options: {
        filters: Array<{ usbVendorId: number; usbProductId: number }>
      }) => Promise<SerialPortHandle>
    }
  }).serial

  if (!window.isSecureContext || !serial) {
    errorMessage.value = '请使用 HTTPS 下的 Chrome 或 Edge。'
    return
  }

  connecting.value = true
  try {
    const port = await serial.requestPort({
      // Read Pico uses Espressif USB Serial/JTAG (VID 303A, PID 1001).
      filters: [{ usbVendorId: 0x303a, usbProductId: 0x1001 }],
    })
    const info = (port as SerialPortHandle & { getInfo: () => SerialPortInfo }).getInfo()
    if (info.usbVendorId !== 0x303a || info.usbProductId !== 0x1001) {
      errorMessage.value = '请选择通过 USB 连接的小纸 Pico。'
      return
    }

    selectedDevice.value = port
    flashState.value = 'ready'
  } catch (error) {
    if (error instanceof DOMException && error.name !== 'NotFoundError') {
      errorMessage.value = '无法选择设备，请检查 USB 连接后重试。'
    }
  } finally {
    connecting.value = false
  }
}

function chooseCustomFirmware(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (file.size !== FLASH_SIZE) {
    customFirmwareFile.value = null
    selectedVersion.value = FACTORY_FIRMWARE.id
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

function validateFactoryImage(data: Uint8Array) {
  const isEsp32s3Image = (offset: number) =>
    data[offset] === 0xe9 && data[offset + 12] === 0x09 && data[offset + 13] === 0x00

  if (data.byteLength !== FLASH_SIZE) {
    throw new Error('固件大小不正确，未写入设备。')
  }
  if (!isEsp32s3Image(0) || data[0x8000] !== 0xaa || data[0x8001] !== 0x50 || !isEsp32s3Image(0x10000)) {
    throw new Error('固件不符合小纸 Pico 整片镜像格式，未写入设备。')
  }
}

async function loadFirmware() {
  if (selectedVersion.value === 'custom') {
    if (!customFirmwareFile.value) throw new Error('请选择固件文件。')
    const data = new Uint8Array(await customFirmwareFile.value.arrayBuffer())
    validateFactoryImage(data)
    return { data, sha256: await sha256(data) }
  }

  const version = firmwareVersions.find(({ id }) => id === selectedVersion.value)
  if (!version) throw new Error('请选择可用固件。')

  const response = await fetch(version.url)
  if (!response.ok) throw new Error('固件下载失败，请检查网络后重试。')
  const data = new Uint8Array(await response.arrayBuffer())
  validateFactoryImage(data)

  const actualHash = await sha256(data)
  if (actualHash !== version.sha256) {
    throw new Error('固件校验失败，未写入设备。')
  }

  return { data, sha256: actualHash }
}

function confirmFullFlashWrite() {
  return new Promise<boolean>((resolve) => {
    const dialog = confirmDialog.value
    if (!dialog) {
      resolve(false)
      return
    }

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
  if (!selectedDevice.value || !(await confirmFullFlashWrite())) return

  flashState.value = 'flashing'
  errorMessage.value = ''
  activeStepIndex.value = 0
  progress.value = 0

  try {
    const firmware = await loadFirmware()
    activeStepIndex.value = 1

    const terminal = {
      clean() {},
      writeLine(_data: string) {},
      write(_data: string) {},
    }
    activeTransport = new Transport(selectedDevice.value, false)
    const loader = new ESPLoader({
      transport: activeTransport,
      baudrate: 460800,
      romBaudrate: 115200,
      terminal,
    })

    const chipName = await loader.main()
    if (!chipName.includes('ESP32-S3')) {
      throw new Error('检测到的不是 ESP32-S3，未写入设备。')
    }

    const detectedFlashSize = await loader.detectFlashSize()
    if (detectedFlashSize !== '16MB') {
      throw new Error('设备 Flash 容量不是 16 MiB，未写入设备。')
    }

    activeStepIndex.value = 2
    progress.value = 0
    await loader.writeFlash({
      fileArray: [{ data: firmware.data, address: 0 }],
      flashMode: 'keep',
      flashFreq: 'keep',
      // This is a complete factory image. Keep its bootloader header unchanged.
      flashSize: 'keep',
      eraseAll: false,
      compress: true,
      reportProgress: (_fileIndex, written, total) => {
        progress.value = total ? Math.min(100, Math.floor((written / total) * 100)) : 0
      },
    })

    activeStepIndex.value = 3
    progress.value = 0
    const deviceHash = await loader.flashMd5sum(0, FLASH_SIZE)
    if (deviceHash !== md5(firmware.data)) {
      throw new Error('写入后校验失败，请保持 USB 连接并重试。')
    }
    progress.value = 100

    activeStepIndex.value = 4
    progress.value = 0
    // ESP32-S3's USB Serial/JTAG port needs an explicit RTS pulse to leave
    // download mode and start the firmware.
    await loader.after('custom_reset', false, 'R1|W100|R0')
    activeStepIndex.value = flashSteps.length
    progress.value = 100
    flashState.value = 'complete'
  } catch (error) {
    const message = error instanceof Error ? error.message : '刷写失败，请保持 USB 连接并重试。'
    setFlashError(message)
  } finally {
    try {
      await activeTransport?.disconnect()
    } catch {
      // A successful reset can disconnect the USB serial device before it closes.
    }
    activeTransport = null
    selectedDevice.value = null
  }
}

function returnToSelection() {
  errorMessage.value = ''
  flashState.value = 'start'
  activeStepIndex.value = 0
  progress.value = 0
}
</script>

<template>
  <main class="flash-page">
    <h1>在线刷机</h1>
    <section class="flash-panel" aria-live="polite" aria-atomic="true">
      <div v-if="flashState === 'flashing' || flashState === 'complete' || flashState === 'error'" class="flash-progress">
        <p class="flash-status">{{ flashState === 'complete' ? '刷机完成' : '正在烧录小纸 Pico · 原厂固件…' }}</p>
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
        <select id="device-model" v-model="selectedModel">
          <option v-for="device in devices" :key="device.id" :value="device.id">
            {{ device.label }}
          </option>
        </select>

        <label class="field-label" for="firmware-version">版本</label>
        <select
          id="firmware-version"
          v-model="selectedVersion"
        >
          <option v-for="version in firmwareVersions" :key="version.id" :value="version.id">
            {{ version.label }}
          </option>
          <option v-if="customFirmwareFile" value="custom">
            自定义 · {{ customFirmwareFile.name }}
          </option>
        </select>

        <VPButton
          :text="connecting ? '正在连接…' : selectedDevice ? '开始刷机' : '连接设备'"
          size="big"
          :disabled="connecting || (selectedDevice !== null && selectedVersion === '')"
          @click="selectedDevice ? startFlashing() : connectDevice()"
        />

        <input
          id="custom-firmware"
          class="visually-hidden"
          type="file"
          accept=".bin,application/octet-stream"
          @change="chooseCustomFirmware"
        />
        <label class="custom-file-link" for="custom-firmware">
          {{ customFirmwareFile ? '更换自定义固件' : '选择自定义固件' }}
        </label>
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
      <h2 id="flash-confirm-title" class="flash-confirm-title">确认刷写原厂固件</h2>
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
  max-width: var(--vp-layout-max-width, 1440px);
  margin-inline: auto;
  align-content: start;
  justify-items: center;
  padding: max(2rem, env(safe-area-inset-top))
    max(1.5rem, env(safe-area-inset-right))
    max(2rem, env(safe-area-inset-bottom))
    max(1.5rem, env(safe-area-inset-left));
}

.flash-panel {
  display: grid;
  width: min(100%, 28rem);
  gap: 1.25rem;
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
