import { Component } from "@angular/core";
import { NgIf } from "@angular/common";
import { Router } from "@angular/router";

import { SubtitleStoreService } from "../subtitle-store.service";


@Component({
  selector: "app-result",
  standalone: true,
  imports: [NgIf],
  templateUrl: "./result.component.html",
  styleUrls: ["./result.component.css"],
})
export class ResultComponent {
  constructor(
    public readonly store: SubtitleStoreService,
    private readonly router: Router
  ) {}

  back(): void {
    this.router.navigateByUrl("/");
  }
}
