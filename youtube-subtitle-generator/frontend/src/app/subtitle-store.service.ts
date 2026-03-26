import { Injectable } from "@angular/core";


@Injectable({ providedIn: "root" })
export class SubtitleStoreService {
  srtPath = "";
  srtContent = "";
  statusMessage = "";

  setStatus(message: string): void {
    this.statusMessage = message;
  }

  setResult(srtPath: string, srtContent: string): void {
    this.srtPath = srtPath;
    this.srtContent = srtContent;
  }

  clear(): void {
    this.srtPath = "";
    this.srtContent = "";
    this.statusMessage = "";
  }
}
