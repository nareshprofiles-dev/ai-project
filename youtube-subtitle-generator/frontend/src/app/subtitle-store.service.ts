import { Injectable } from "@angular/core";

export type ReviewRow = {
  id: number;
  start: number;
  end: number;
  teluguOriginal: string;
  teluguCurrent: string;
  englishOriginal: string;
  englishCurrent: string;
  edited: boolean;
  needsRetranslate: boolean;
};


@Injectable({ providedIn: "root" })
export class SubtitleStoreService {
  url = "";
  model = "large-v3";
  outputDir = "output";
  reviewRows: ReviewRow[] = [];
  srtPath = "";
  srtContent = "";
  statusMessage = "";

  setStatus(message: string): void {
    this.statusMessage = message;
  }

  setRequest(url: string, model: string, outputDir: string): void {
    this.url = url;
    this.model = model;
    this.outputDir = outputDir;
  }

  setReviewRows(rows: ReviewRow[]): void {
    this.reviewRows = rows.map((r) => ({ ...r }));
  }

  setResult(srtPath: string, srtContent: string): void {
    this.srtPath = srtPath;
    this.srtContent = srtContent;
  }

  clear(): void {
    this.url = "";
    this.model = "large-v3";
    this.outputDir = "output";
    this.reviewRows = [];
    this.srtPath = "";
    this.srtContent = "";
    this.statusMessage = "";
  }
}
