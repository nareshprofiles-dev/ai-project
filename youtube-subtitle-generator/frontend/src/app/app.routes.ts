import { Routes } from "@angular/router";

import { GenerateComponent } from "./components/generate.component";
import { ResultComponent } from "./components/result.component";


export const appRoutes: Routes = [
  { path: "", component: GenerateComponent },
  { path: "result", component: ResultComponent },
  { path: "**", redirectTo: "" },
];
