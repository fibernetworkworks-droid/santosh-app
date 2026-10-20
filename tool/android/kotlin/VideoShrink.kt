package com.newtika.santosh

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.audio.AudioProcessor
import androidx.media3.common.Effect
import androidx.media3.effect.FrameDropEffect
import androidx.media3.effect.Presentation
import androidx.media3.transformer.Composition
import androidx.media3.transformer.DefaultEncoderFactory
import androidx.media3.transformer.EditedMediaItem
import androidx.media3.transformer.EditedMediaItemSequence
import androidx.media3.transformer.Effects
import androidx.media3.transformer.ExportException
import androidx.media3.transformer.ExportResult
import androidx.media3.transformer.ProgressHolder
import androidx.media3.transformer.Transformer
import androidx.media3.transformer.VideoEncoderSettings
import java.io.File

/** Shrinks a phone video so it fits Hoola's 25 MB file limit (Android's own encoder via Jetpack Media3, Apache-2.0).
 *  v0.56: progress + cancel, HDR phone videos are tone-mapped to normal video, 60 fps drops to 30 fps at low bitrates,
 *  a second smaller pass when the first comes out too big, a safe retry (480p, no HDR mode) when the encoder refuses,
 *  and long videos: "too_long:<max ms>" so the app can offer to send the first part (clipMs).
 *  One job at a time; everything runs on the main looper. */
object VideoShrink {
    private val main = Handler(Looper.getMainLooper())
    private var job: Transformer? = null
    private var jobDone: ((String?, String?) -> Unit)? = null
    private var jobOut: File? = null
    private var passBase = 0      // progress of earlier passes (0 or 50)
    private var passSpan = 100
    private val holder = ProgressHolder()

    private const val AUDIO_BPS = 128_000L
    private const val MIN_VIDEO_BPS = 250_000L

    fun maxMs(targetMb: Int): Long = budgetBits(targetMb) * 1000 / (MIN_VIDEO_BPS + AUDIO_BPS)

    private fun budgetBits(targetMb: Int): Long = targetMb.toLong() * 1024 * 1024 * 8 * 9 / 10

    /** 0..100 while a job runs, -1 when nothing is running. */
    fun progress(): Int {
        val t = job ?: return -1
        return try {
            if (t.getProgress(holder) == Transformer.PROGRESS_STATE_AVAILABLE) passBase + holder.progress * passSpan / 100 else passBase
        } catch (_: Exception) { passBase }
    }

    fun cancel() {
        val t = job ?: return
        try { t.cancel() } catch (_: Exception) {}
        jobOut?.delete()
        finish(null, "cancelled")
    }

    private fun finish(out: String?, err: String?) {
        val d = jobDone
        job = null; jobDone = null; jobOut = null
        d?.invoke(out, err)
    }

    fun run(ctx: Context, path: String, targetMb: Int, clipMs: Long = 0, done: (String?, String?) -> Unit) {
        main.post {
            if (job != null) { done(null, "ek video pehle se chhoti ho rahi hai"); return@post }
            try {
                val src = File(path)
                if (!src.exists()) { done(null, "file nahi mili"); return@post }
                var durMs = 0L
                var fps = 30f
                try {
                    MediaMetadataRetriever().run {
                        setDataSource(path)
                        durMs = extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
                        if (Build.VERSION.SDK_INT >= 28 && durMs > 0) {
                            val frames = extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT)?.toFloatOrNull()
                            if (frames != null && frames > 0) fps = frames * 1000f / durMs
                        }
                        release()
                    }
                } catch (_: Exception) {}
                if (durMs <= 0) { done(null, "video ki lambai pata nahi chali"); return@post }
                val useMs = if (clipMs in 1 until durMs) clipMs else durMs
                if (useMs > maxMs(targetMb)) { done(null, "too_long:${maxMs(targetMb)}"); return@post }
                jobDone = done
                passBase = 0; passSpan = 100
                start(ctx, src, targetMb, useMs, if (useMs < durMs) useMs else 0L, fps, 1.0, safe = false, pass = 1)
            } catch (e: Exception) {
                finish(null, "video chhota nahi ho paya (${e.javaClass.simpleName})")
            }
        }
    }

    private fun start(ctx: Context, src: File, targetMb: Int, useMs: Long, clipMs: Long, fps: Float, scale: Double,
                      safe: Boolean, pass: Int) {
        val videoBps = ((budgetBits(targetMb) * 1000 / useMs - AUDIO_BPS) * scale).toLong().coerceIn(MIN_VIDEO_BPS * 3 / 4, 2_500_000)
        val height = if (safe || videoBps < 1_200_000) 480 else 720
        val out = File(ctx.cacheDir, "shrunk_${System.currentTimeMillis()}.mp4")
        jobOut = out
        val enc = DefaultEncoderFactory.Builder(ctx)
            .setRequestedVideoEncoderSettings(VideoEncoderSettings.Builder().setBitrate(videoBps.toInt()).build())
            .setEnableFallback(true)
            .build()
        val mi = MediaItem.Builder().setUri(Uri.fromFile(src))
        if (clipMs > 0) mi.setClippingConfiguration(MediaItem.ClippingConfiguration.Builder().setEndPositionMs(clipMs).build())
        val video = ArrayList<Effect>()
        if (fps > 31f && videoBps < 1_500_000) video.add(FrameDropEffect.createDefaultFrameDropEffect(30f))
        video.add(Presentation.createForHeight(height))
        val item = EditedMediaItem.Builder(mi.build())
            .setEffects(Effects(listOf<AudioProcessor>(), video))
            .build()
        val comp = Composition.Builder(EditedMediaItemSequence(item)).apply {
            // HDR phone videos (Samsung, Pixel, iPhone clips) -> normal video, so every phone can play the result
            if (!safe && Build.VERSION.SDK_INT >= 29) setHdrMode(Composition.HDR_MODE_TONE_MAP_HDR_TO_SDR_USING_OPEN_GL)
        }.build()
        val t = Transformer.Builder(ctx)
            .setVideoMimeType(MimeTypes.VIDEO_H264)
            .setAudioMimeType(MimeTypes.AUDIO_AAC)
            .setEncoderFactory(enc)
            .addListener(object : Transformer.Listener {
                override fun onCompleted(composition: Composition, exportResult: ExportResult) {
                    if (job == null) return     // cancelled meanwhile
                    val limit = targetMb.toLong() * 1024 * 1024
                    val size = out.length()
                    if (size > limit && pass == 1) {
                        // the encoder gave more than asked: one more, smaller pass from the original
                        out.delete()
                        passBase = 50; passSpan = 50
                        val again = (scale * limit.toDouble() / size.toDouble() * 0.9).coerceIn(0.3, 0.9)
                        main.post { start(ctx, src, targetMb, useMs, clipMs, fps, again, safe, 2) }
                        return
                    }
                    if (size > limit) { out.delete(); finish(null, "chhota karke bhi 25 MB se badi hai"); return }
                    finish(out.absolutePath, null)
                }

                override fun onError(composition: Composition, exportResult: ExportResult, exportException: ExportException) {
                    out.delete()
                    if (job == null) return
                    if (!safe) {
                        // some encoders refuse HDR tone-mapping / 720p / the bitrate: try once more the plain way
                        main.post { start(ctx, src, targetMb, useMs, clipMs, 30f, scale, safe = true, pass = pass) }
                        return
                    }
                    finish(null, "video chhota nahi ho paya (${exportException.errorCodeName})")
                }
            })
            .build()
        job = t
        t.start(comp, out.absolutePath)
    }
}
