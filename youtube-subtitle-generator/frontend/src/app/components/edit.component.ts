import { Component } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { NgFor, NgIf } from "@angular/common";
import { Router } from "@angular/router";

import { SubtitleStoreService, ReviewRow } from "../subtitle-store.service";


type FinalizeResponse = {
  srt_path: string;
  srt_content: string;
  error?: string;
};

type RetranslateResponse = {
  id: number;
  english_text: string;
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
  retranslatingId: number | null = null;

  constructor(
    public readonly store: SubtitleStoreService,
    private readonly router: Router
  ) {}

  onTeluguEdit(row: ReviewRow): void {
    row.edited = true;
    row.needsRetranslate = true;
  }

  async retranslate(row: ReviewRow): Promise<void> {
    this.error = "";
    this.retranslatingId = row.id;

    try {
      const response = await fetch("http://localhost:8000/api/retranslate-sentence/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: row.id,
          start: row.start,
          end: row.end,
          telugu_text: row.teluguCurrent,
        }),
      });

      const data = (await response.json()) as RetranslateResponse;
      if (!response.ok) {
        this.error = data.error || "Retranslation failed.";
        return;
      }

      row.englishCurrent = data.english_text;
      row.needsRetranslate = false;
    } catch (err: unknown) {
      this.error = err instanceof Error ? err.message : "Unexpected error during retranslation.";
    } finally {
      this.retranslatingId = null;
    }
  }

  async finalize(): Promise<void> {
    this.error = "";

    if (!this.store.reviewRows.length) {
      this.error = "No subtitle data found. Please go back and generate subtitles first.";
      return;
    }

    this.isLoading = true;
    this.store.setStatus("Generating final SRT from reviewed subtitles...");

    try {
      const response = await fetch("http://localhost:8000/api/finalize-subtitles/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rows: this.store.reviewRows.map((r) => ({
            id: r.id,
            start: r.start,
            end: r.end,
            telugu_current: r.teluguCurrent,
            english_current: r.englishCurrent,
          })),
          output_dir: this.store.outputDir,
        }),
      });

      const data = (await response.json()) as FinalizeResponse;
      if (!response.ok) {
        this.error = data.error || "Failed to finalize subtitles.";
        this.store.setStatus("");
        return;
      }

      this.store.setResult(data.srt_path, data.srt_content);
      this.store.setStatus("Done.");
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
