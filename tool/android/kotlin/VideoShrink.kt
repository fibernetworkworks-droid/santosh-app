package com.newtika.santosh

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Handler
import android.os.Looper
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.effect.Presentation
import androidx.media3.transformer.Composition
import androidx.media3.transformer.DefaultEncoderFactory
import androidx.media3.transformer.EditedMediaItem
import androidx.media3.transformer.Effects
import androidx.media3.transformer.ExportException
import androidx.media3.transformer.ExportResult
import androidx.media3.transformer.Transformer
import androidx.media3.transformer.VideoEncoderSettings
import java.io.File

/** v0.49 Shrinks a phone video so it fits Hoola's 25 MB file limit (Android's own encoder via Jetpack Media3,
 *  Apache-2.0): bitrate from the duration, 720p (or 480p for long videos), H.264 + AAC. Runs on the main looper. */
object VideoShrink {
    private val main = Handler(Looper.getMainLooper())

    fun run(ctx: Context, path: String, targetMb: Int, done: (String?, String?) -> Unit) {
        main.post {
            try {
                val src = File(path)
                if (!src.exists()) { done(null, "file nahi mili"); return@post }
                val durMs = try {
                    MediaMetadataRetriever().run {
                        setDataSource(path)
                        val d = extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
                        release(); d
                    }
                } catch (_: Exception) { 0L }
                if (durMs <= 0) { done(null, "video ki lambai pata nahi chali"); return@post }
                val totalBits = targetMb.toLong() * 1024 * 1024 * 8 * 9 / 10
                val videoBps = (totalBits * 1000 / durMs - 128_000).coerceAtMost(2_500_000)
                if (videoBps < 250_000) { done(null, "video bahut lambi hai (${durMs / 60000} min); chhota hissa bhejiye"); return@post }
                val height = if (videoBps >= 1_200_000) 720 else 480
                val out = File(ctx.cacheDir, "shrunk_${System.currentTimeMillis()}.mp4")
                val enc = DefaultEncoderFactory.Builder(ctx)
                    .setRequestedVideoEncoderSettings(VideoEncoderSettings.Builder().setBitrate(videoBps.toInt()).build())
                    .build()
                val item = EditedMediaItem.Builder(MediaItem.fromUri(Uri.fromFile(src)))
                    .setEffects(Effects(listOf(), listOf(Presentation.createForHeight(height))))
                    .build()
                val t = Transformer.Builder(ctx)
                    .setVideoMimeType(MimeTypes.VIDEO_H264)
                    .setAudioMimeType(MimeTypes.AUDIO_AAC)
                    .setEncoderFactory(enc)
                    .addListener(object : Transformer.Listener {
                        override fun onCompleted(composition: Composition, exportResult: ExportResult) {
                            done(out.absolutePath, null)
                        }

                        override fun onError(composition: Composition, exportResult: ExportResult, exportException: ExportException) {
                            out.delete()
                            done(null, "video chhota nahi ho paya (${exportException.errorCodeName})")
                        }
                    })
                    .build()
                t.start(item, out.absolutePath)
            } catch (e: Exception) {
                done(null, "video chhota nahi ho paya (${e.javaClass.simpleName})")
            }
        }
    }
}
