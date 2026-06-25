import { Component } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { NgIf, NgFor } from "@angular/common";
import { Router } from "@angular/router";

import { SubtitleStoreService } from "../subtitle-store.service";


type ReviewUnitRow = {
  id: number;
  start: number;
  end: number;
  telugu_original: string;
  telugu_current: string;
  english_original: string;
  english_current: string;
  source_timeline: string;
  edited: boolean;
  needs_retranslate: boolean;
};

type ReviewUnitsResponse = {
  rows: ReviewUnitRow[];
  error?: string;
};


@Component({
  selector: "app-generate",
  standalone: true,
  imports: [FormsModule, NgIf, NgFor],
  templateUrl: "./generate.component.html",
  styleUrls: ["./generate.component.css"],
})
export class GenerateComponent {
  url = "";
  model = "large-v3";
  outputDir = "output";
  isLoading = false;
  error = "";

  models = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"];

  constructor(
    private readonly router: Router,
    public readonly store: SubtitleStoreService
  ) {}

  async generate(): Promise<void> {
    this.error = "";
    this.store.clear();

    if (!this.url.trim()) {
      this.error = "Please enter a YouTube URL.";
      return;
    }

    this.isLoading = true;
    this.store.setStatus(
      "Transcribing and translating Telugu audio. This may take several minutes..."
    );

    try {
      const data = await this.fetchReviewUnits();

      this.store.setRequest(this.url.trim(), this.model, this.outputDir.trim() || "output");
      this.store.setReviewRows(
        (data.rows || []).map((r) => ({
          id: r.id,
          start: r.start,
          end: r.end,
          teluguOriginal: r.telugu_original,
          teluguCurrent: r.telugu_current,
          englishOriginal: r.english_original,
          englishCurrent: r.english_current,
          edited: r.edited,
          needsRetranslate: r.needs_retranslate,
        }))
      );
      this.store.setStatus("Review ready. Edit either side, then finalize.");
      await this.router.navigateByUrl("/edit");
    } catch (err: unknown) {
      this.error = err instanceof Error ? err.message : "Unexpected error.";
      this.store.setStatus("");
    } finally {
      this.isLoading = false;
    }
  }

  private async fetchReviewUnits(attempt = 1): Promise<ReviewUnitsResponse> {
    const body = JSON.stringify({
      url: this.url.trim(),
      model: this.model,
      output_dir: this.outputDir.trim() || "output",
    });

    let response: Response;
    try {
      response = await fetch("http://localhost:8000/api/review-units/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
    } catch (networkErr) {
      // Connection dropped mid-request (broken pipe / TCP timeout).
      // The server may have finished and cached results, so retry once.
      if (attempt === 1) {
        this.store.setStatus("Connection dropped — retrying (results may be cached)...");
        await new Promise((resolve) => setTimeout(resolve, 2000));
        return this.fetchReviewUnits(2);
      }
      throw networkErr;
    }

    const data = (await response.json()) as ReviewUnitsResponse;
    if (!response.ok) {
      throw new Error(data.error || "Failed to generate review units.");
    }
    return data;
  }
}
