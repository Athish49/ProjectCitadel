import fs from "fs";
import path from "path";

export interface DocMeta {
  slug: string;
  filename: string;
  shortTitle: string;
  number: string;
  description: string;
}

export const DOCS: DocMeta[] = [
  {
    slug: "01-prd",
    filename: "01_PRD_Product_Requirements.md",
    shortTitle: "PRD",
    number: "01",
    description: "Product requirements, user stories, acceptance criteria",
  },
  {
    slug: "02-tad",
    filename: "02_Technical_Architecture.md",
    shortTitle: "TAD",
    number: "02",
    description: "System architecture, defense patterns, agent design",
  },
  {
    slug: "03-data-model",
    filename: "03_Data_Model_Schema.md",
    shortTitle: "Data Model",
    number: "03",
    description: "Database schema, RLS policies, data classification",
  },
  {
    slug: "04-threat-model",
    filename: "04_Security_Threat_Model.md",
    shortTitle: "Threat Model",
    number: "04",
    description: "79-category attack taxonomy, threat analysis, residual risks",
  },
  {
    slug: "05-roadmap",
    filename: "05_Implementation_Roadmap.md",
    shortTitle: "Roadmap",
    number: "05",
    description: "Sprint-by-sprint implementation plan, milestones",
  },
  {
    slug: "06-showcase-spec",
    filename: "06_Showcase_Platform_Spec.md",
    shortTitle: "Console Spec",
    number: "06",
    description: "Resilience Console design system, pages, interaction patterns",
  },
];

const DOCS_DIR = path.join(process.cwd(), "..", "development_docs");

export function getDocContent(filename: string): string {
  const filePath = path.join(DOCS_DIR, filename);
  return fs.readFileSync(filePath, "utf-8");
}

export function getDocBySlug(slug: string): DocMeta | undefined {
  return DOCS.find((d) => d.slug === slug);
}
