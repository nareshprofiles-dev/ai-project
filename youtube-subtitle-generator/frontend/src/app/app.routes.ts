import { Routes } from "@angular/router";

import { EditComponent } from "./components/edit.component";
import { GenerateComponent } from "./components/generate.component";
import { ResultComponent } from "./components/result.component";


export const appRoutes: Routes = [
  { path: "", component: GenerateComponent },
  { path: "edit", component: EditComponent },
  { path: "result", component: ResultComponent },
  { path: "**", redirectTo: "" },
];
