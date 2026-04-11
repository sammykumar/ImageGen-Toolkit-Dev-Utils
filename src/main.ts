import { app } from '../../../scripts/app.js'

type WidgetLike = {
	name?: string
	value?: unknown
	callback?: (...args: unknown[]) => unknown
}

type DOMWidgetLike = {
	onRemove?: () => void
}

type LoadVideoPreviewState = {
	sync: () => void
	cleanup: () => void
}

type NodeLike = {
	widgets?: WidgetLike[]
	size?: [number, number]
	addDOMWidget?: (
		name: string,
		type: string,
		element: HTMLElement,
		options?: Record<string, unknown>
	) => DOMWidgetLike
	computeSize?: () => [number, number]
	setSize?: (size: [number, number]) => void
	onRemoved?: (...args: unknown[]) => unknown
	__loadVideoUrlPreviewState?: LoadVideoPreviewState
}

type NodeDefinitionLike = {
	name?: string
}

type NodeTypeLike = {
	prototype: NodeLike & {
		onNodeCreated?: (...args: unknown[]) => unknown
		onConfigure?: (...args: unknown[]) => unknown
	}
}

type ExtensionLike = {
	name: string
	beforeRegisterNodeDef?: (nodeType: NodeTypeLike, nodeData: NodeDefinitionLike) => void
}

const TARGET_NODE_NAME = 'load-video-url'
const PREVIEW_WIDGET_NAME = 'video_url_preview'
const MIN_NODE_WIDTH = 320
const PREVIEW_HEIGHT = 180

function getVideoUrlWidget(node: NodeLike): WidgetLike | undefined {
	return node.widgets?.find((widget) => widget.name === 'video_url')
}

function isPreviewableMp4Url(value: unknown): value is string {
	if (typeof value !== 'string') {
		return false
	}

	const normalizedValue = value.trim()
	if (!normalizedValue) {
		return false
	}

	try {
		const parsed = new URL(normalizedValue)
		return (
			(parsed.protocol === 'http:' || parsed.protocol === 'https:') &&
			parsed.pathname.toLowerCase().endsWith('.mp4')
		)
	} catch {
		return false
	}
}

function resizeNodeForPreview(node: NodeLike) {
	const computedSize = node.computeSize?.()
	if (!computedSize) {
		return
	}

	const nextSize: [number, number] = [
		Math.max(computedSize[0], MIN_NODE_WIDTH),
		Math.max(computedSize[1], PREVIEW_HEIGHT + 120)
	]

	if (typeof node.setSize === 'function') {
		node.setSize(nextSize)
		return
	}

	node.size = nextSize
}

function attachPreview(node: NodeLike) {
	if (node.__loadVideoUrlPreviewState || typeof node.addDOMWidget !== 'function') {
		return
	}

	const wrapper = document.createElement('div')
	wrapper.style.display = 'none'
	wrapper.style.width = '100%'
	wrapper.style.padding = '8px 0 0'

	const video = document.createElement('video')
	video.controls = true
	video.autoplay = true
	video.loop = true
	video.muted = true
	video.playsInline = true
	video.preload = 'metadata'
	video.style.width = '100%'
	video.style.maxHeight = `${PREVIEW_HEIGHT}px`
	video.style.display = 'block'
	video.style.objectFit = 'contain'
	video.style.background = '#111'
	video.style.borderRadius = '8px'

	wrapper.append(video)

	node.addDOMWidget(PREVIEW_WIDGET_NAME, 'preview', wrapper, {
		serialize: false,
		hideOnZoom: false,
		getValue() {
			return null
		},
		setValue() {
			return undefined
		}
	})

	const sync = () => {
		const widget = getVideoUrlWidget(node)
		const rawValue = typeof widget?.value === 'string' ? widget.value : ''
		const nextUrl = rawValue.trim()

		if (!isPreviewableMp4Url(nextUrl)) {
			wrapper.style.display = 'none'
			video.pause()
			video.removeAttribute('src')
			video.load()
			resizeNodeForPreview(node)
			return
		}

		wrapper.style.display = 'block'
		if (video.dataset.previewUrl !== nextUrl) {
			video.dataset.previewUrl = nextUrl
			video.src = nextUrl
			video.load()
		}

		void video.play().catch(() => undefined)
		resizeNodeForPreview(node)
	}

	const cleanup = () => {
		video.pause()
		video.removeAttribute('src')
		video.load()
	}

	const widget = getVideoUrlWidget(node)
	const originalCallback = widget?.callback
	if (widget) {
		widget.callback = function (...args: unknown[]) {
			const callbackResult = originalCallback?.apply(this, args)
			sync()
			return callbackResult
		}
	}

	const originalOnRemoved = node.onRemoved
	node.onRemoved = function (...args: unknown[]) {
		cleanup()
		return originalOnRemoved?.apply(this, args)
	}

	node.__loadVideoUrlPreviewState = {
		sync,
		cleanup
	}

	sync()
}

app.registerExtension({
	name: 'imagegen-toolkit-dev-utils.load-video-url-preview',
	beforeRegisterNodeDef(nodeType, nodeData) {
		if (nodeData.name !== TARGET_NODE_NAME) {
			return
		}

		const originalOnNodeCreated = nodeType.prototype.onNodeCreated
		nodeType.prototype.onNodeCreated = function (...args: unknown[]) {
			const result = originalOnNodeCreated?.apply(this, args)
			attachPreview(this)
			return result
		}

		const originalOnConfigure = nodeType.prototype.onConfigure
		nodeType.prototype.onConfigure = function (...args: unknown[]) {
			const result = originalOnConfigure?.apply(this, args)
			attachPreview(this)
			this.__loadVideoUrlPreviewState?.sync()
			return result
		}
	}
})