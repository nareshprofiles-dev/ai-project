import { Component } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { NgFor, NgIf } from "@angular/common";
import { Router } from "@angular/router";

import { SubtitleStoreService } from "../subtitle-store.service";


type TranslateResponse = {
  srt_path: string;
  srt_content: string;
  error?: string;
};


@Component({
  selector: "app-edit",
  standalone: true,
  imports: [FormsModule, NgFor, NgIf],
  templateUrl: "./edit.component.html",
  styleUrls: ["./edit.component.css"],
})
export class EditComponent {
  isLoading = false;
  error = "";

  constructor(
    public readonly store: SubtitleStoreService,
    private readonly router: Router
  ) {}

  async continueToSubtitles(): Promise<void> {
    this.error = "";

    if (!this.store.segments.length) {
      this.error = "No Telugu transcription found. Please generate subtitles first.";
      return;
    }

    this.isLoading = true;
    this.store.setStatus("Generating subtitles from reviewed Telugu text...");

    try {
      const response = await fetch("http://localhost:8000/api/translate/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: this.store.url,
          model: this.store.model,
          output_dir: this.store.outputDir,
          segments: this.store.segments,
        }),
      });

      const data = (await response.json()) as TranslateResponse;
      if (!response.ok) {
        this.error = data.error || "Failed to generate subtitles.";
        this.store.setStatus("");
        return;
      }

      this.store.setResult(data.srt_path, data.srt_content);
      this.store.setStatus("Done. Opening subtitle output...");
      await this.router.navigateByUrl("/result");
    } catch (err: unknown) {
      this.error = err instanceof Error ? err.message : "Unexpected error.";
      this.store.setStatus("");
    } finally {
      this.isLoading = false;
    }
  }

  back(): void {
    this.router.navigateByUrl("/");
  }

  formatTimestamp(value: number): string {
    const totalSeconds = Math.max(0, Math.floor(value));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  }
}
