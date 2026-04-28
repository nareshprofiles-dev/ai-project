import { Injectable } from "@angular/core";

export type SubtitleSegment = {
  id: number;
  start: number;
  end: number;
  text: string;
};


@Injectable({ providedIn: "root" })
export class SubtitleStoreService {
  url = "";
  model = "large-v3";
  outputDir = "output";
  segments: SubtitleSegment[] = [];
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

  setSegments(segments: SubtitleSegment[]): void {
    this.segments = segments.map((segment) => ({ ...segment }));
  }

  setResult(srtPath: string, srtContent: string): void {
    this.srtPath = srtPath;
    this.srtContent = srtContent;
  }

  clear(): void {
    this.url = "";
    this.model = "large-v3";
    this.outputDir = "output";
    this.segments = [];
    this.srtPath = "";
    this.srtContent = "";
    this.statusMessage = "";
  }
}
