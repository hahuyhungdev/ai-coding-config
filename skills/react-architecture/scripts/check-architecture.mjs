#!/usr/bin/env node
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const rootDir = path.resolve(process.argv[2] ?? process.cwd());
const srcDir = path.join(rootDir, "src");
const sourceExtensions = new Set([".ts", ".tsx"]);
const ignoredSourcePatterns = [/\.test\./, /\.spec\./, /\/testing\//];
const requireFromProject = createRequire(path.join(rootDir, "package.json"));
const flatSharedEntries = new Set(["assets", "components", "hooks", "types", "utils"]);

let ts;
try {
  ts = requireFromProject("typescript");
} catch {
  console.error("Could not load 'typescript' from the target project.");
  console.error("Install project dependencies first, or run this from a project with TypeScript installed.");
  process.exit(1);
}

function toPosix(filePath) {
  return filePath.split(path.sep).join("/");
}

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) return walk(fullPath);
    if (!sourceExtensions.has(path.extname(entry.name))) return [];

    const relative = toPosix(path.relative(srcDir, fullPath));
    if (ignoredSourcePatterns.some((pattern) => pattern.test(relative))) return [];
    return [fullPath];
  });
}

function stripKnownExtension(relativePath) {
  return relativePath.replace(/\.(tsx?|jsx?|s?css)$/u, "");
}

function getLayer(relativePath) {
  const [layer, name] = relativePath.split("/");
  if (layer === "shared") return { layer: "shared" };
  if (!fs.existsSync(path.join(srcDir, "shared")) && flatSharedEntries.has(layer)) {
    return { layer: "shared" };
  }
  if (layer === "features") return { layer: "features", feature: name };
  if (layer === "pages") return { layer: "pages" };
  if (layer === "layouts") return { layer: "layouts" };
  if (layer === "styles") return { layer: "styles" };
  return { layer: "app" };
}

function resolveInternalImport(fromFile, specifier) {
  if (specifier.startsWith("@/")) {
    return stripKnownExtension(specifier.slice(2));
  }

  if (!specifier.startsWith(".")) {
    return null;
  }

  const resolved = path.resolve(path.dirname(fromFile), specifier);
  if (!resolved.startsWith(srcDir)) {
    return null;
  }

  return stripKnownExtension(toPosix(path.relative(srcDir, resolved)));
}

function isFeaturePublicEntry(targetPath) {
  const parts = targetPath.split("/");
  if (parts[0] !== "features" || parts.length < 2) return false;
  return parts.length === 2 || (parts.length === 3 && parts[2] === "index");
}

function getModuleSpecifiers(filePath) {
  const text = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    text,
    ts.ScriptTarget.Latest,
    true,
    filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );

  const specifiers = [];

  function visit(node) {
    if (
      (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
      node.moduleSpecifier &&
      ts.isStringLiteral(node.moduleSpecifier)
    ) {
      specifiers.push(node.moduleSpecifier.text);
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return specifiers;
}

function getInlineStyleProps(filePath) {
  if (!filePath.endsWith(".tsx")) return [];

  const text = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    text,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const locations = [];

  function visit(node) {
    if (ts.isJsxAttribute(node) && node.name.text === "style") {
      const position = sourceFile.getLineAndCharacterOfPosition(node.name.getStart(sourceFile));
      locations.push({ line: position.line + 1 });
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return locations;
}

function validateImport(fromRelative, toRelative, specifier) {
  const from = getLayer(fromRelative);
  const to = getLayer(toRelative);

  if (from.layer === "app") return null;

  if (from.layer === "shared") {
    if (to.layer === "shared") return null;
    return "shared code may only import other shared code";
  }

  if (from.layer === "layouts") {
    if (to.layer === "shared") return null;
    return "layouts may only import shared code";
  }

  if (from.layer === "features") {
    if (to.layer === "shared") return null;
    if (to.layer === "features" && from.feature === to.feature) return null;
    return "features may import shared code and same-feature files only";
  }

  if (from.layer === "pages") {
    if (to.layer === "shared" || to.layer === "layouts") return null;
    if (isFeaturePublicEntry(toRelative)) return null;
    if (to.layer === "features") {
      return "pages must import features through their public index";
    }
    return "pages may import shared, layouts, and feature public indexes only";
  }

  return `unsupported import from ${from.layer} to ${to.layer}: ${specifier}`;
}

if (!fs.existsSync(srcDir)) {
  console.error(`No src directory found at ${srcDir}`);
  process.exit(1);
}

const files = walk(srcDir);
const violations = [];
const styleViolations = [];
const structureViolations = [];

function getReExportSpecifiers(filePath) {
  const text = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    text,
    ts.ScriptTarget.Latest,
    true,
    filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );

  const specifiers = [];

  function visit(node) {
    if (
      ts.isExportDeclaration(node) &&
      node.moduleSpecifier &&
      ts.isStringLiteral(node.moduleSpecifier)
    ) {
      specifiers.push(node.moduleSpecifier.text);
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return specifiers;
}

function getImportedValueBindings(sourceFile) {
  const bindings = new Set();

  for (const statement of sourceFile.statements) {
    if (!ts.isImportDeclaration(statement) || !statement.importClause) continue;
    if (statement.importClause.isTypeOnly) continue;

    if (statement.importClause.name) {
      bindings.add(statement.importClause.name.text);
    }

    const namedBindings = statement.importClause.namedBindings;
    if (!namedBindings) continue;

    if (ts.isNamespaceImport(namedBindings)) {
      bindings.add(namedBindings.name.text);
      continue;
    }

    for (const element of namedBindings.elements) {
      if (element.isTypeOnly) continue;
      bindings.add(element.name.text);
    }
  }

  return bindings;
}

function getImportedFeatureIndexExports(filePath) {
  const text = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    text,
    ts.ScriptTarget.Latest,
    true,
    filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const importedBindings = getImportedValueBindings(sourceFile);
  const exportedImportedBindings = [];

  function visit(node) {
    if (
      ts.isExportDeclaration(node) &&
      !node.moduleSpecifier &&
      !node.isTypeOnly &&
      node.exportClause &&
      ts.isNamedExports(node.exportClause)
    ) {
      for (const element of node.exportClause.elements) {
        if (element.isTypeOnly) continue;
        const localName = element.propertyName?.text ?? element.name.text;
        if (importedBindings.has(localName)) {
          exportedImportedBindings.push(localName);
        }
      }
    }

    if (ts.isExportAssignment(node) && ts.isIdentifier(node.expression)) {
      const localName = node.expression.text;
      if (importedBindings.has(localName)) {
        exportedImportedBindings.push(localName);
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return exportedImportedBindings;
}

function getComponentStructureViolation(relativeFile) {
  const parts = relativeFile.split("/");
  const fileName = parts.at(-1);

  if (!relativeFile.endsWith(".tsx")) return null;

  // 1. Feature component structure: features/<feature-name>/components/<ComponentName>/index.tsx
  if (parts[0] === "features" && parts[2] === "components") {
    if (parts.length < 5) {
      return `feature components must be in a subfolder, e.g. components/Foo/index.tsx (got: ${relativeFile})`;
    }
    const componentDir = parts[3];
    if (fileName !== "index.tsx") {
      return `feature component file must be components/${componentDir}/index.tsx (got: ${fileName})`;
    }
  }

  // 2. Shared component structure
  const hasSharedRoot = fs.existsSync(path.join(srcDir, "shared"));
  if (hasSharedRoot && parts[0] === "shared" && parts[1] === "components") {
    if (parts.length < 4) {
      return `shared components must be in a subfolder, e.g. shared/components/Foo/index.tsx (got: ${relativeFile})`;
    }
    const componentDir = parts[parts.length - 2];
    if (fileName !== "index.tsx") {
      return `shared component file must be components/${componentDir}/index.tsx (got: ${fileName})`;
    }
  } else if (!hasSharedRoot && parts[0] === "components") {
    // For projects where shared components are direct under components/
    if (parts.length >= 3) {
      const componentDir = parts[parts.length - 2];
      if (fileName !== "index.tsx") {
        return `shared component file must be components/${componentDir}/index.tsx (got: ${fileName})`;
      }
    }
  }

  return null;
}

for (const filePath of files) {
  const fromRelative = stripKnownExtension(toPosix(path.relative(srcDir, filePath)));
  const relativeFile = toPosix(path.relative(srcDir, filePath));

  const componentStructureReason = getComponentStructureViolation(relativeFile);
  if (componentStructureReason) {
    structureViolations.push({
      file: relativeFile,
      reason: componentStructureReason,
    });
  }

  if (/^features\/[^/]+\/index$/u.test(fromRelative)) {
    for (const specifier of getReExportSpecifiers(filePath)) {
      structureViolations.push({
        file: relativeFile,
        reason: `feature indexes must compose the public component, not re-export "${specifier}"`,
      });
    }
    for (const binding of getImportedFeatureIndexExports(filePath)) {
      structureViolations.push({
        file: relativeFile,
        reason: `feature indexes must define public components, not export imported component "${binding}"`,
      });
    }
  }

  for (const specifier of getModuleSpecifiers(filePath)) {
    if (/\.(css|scss)$/u.test(specifier)) continue;

    const toRelative = resolveInternalImport(filePath, specifier);
    if (!toRelative) continue;

    const reason = validateImport(fromRelative, toRelative, specifier);
    if (reason) {
      violations.push({
        file: `${fromRelative}${path.extname(filePath)}`,
        specifier,
        reason,
      });
    }

    const fromParts = fromRelative.split("/");
    const toParts = toRelative.split("/");
    if (fromParts[0] === "features" && fromParts[2] === "components") {
      const sameFeature = toParts[0] === "features" && toParts[1] === fromParts[1];

      if (sameFeature && toParts[2] === "hooks") {
        structureViolations.push({
          file: relativeFile,
          reason: `feature component imports hook "${specifier}"; compose feature hooks in features/${fromParts[1]}/index.tsx`,
        });
      }
    }
  }

  for (const location of getInlineStyleProps(filePath)) {
    styleViolations.push({
      file: `${fromRelative}${path.extname(filePath)}`,
      line: location.line,
    });
  }
}

if (violations.length > 0 || styleViolations.length > 0 || structureViolations.length > 0) {
  if (structureViolations.length > 0) {
    console.error("Structure violations found:\n");
    for (const violation of structureViolations) {
      console.error(`- src/${violation.file}`);
      console.error(`  ${violation.reason}`);
    }
    console.error("");
  }

  if (styleViolations.length > 0) {
    console.error("Inline style props found:\n");
    for (const violation of styleViolations) {
      console.error(`- src/${violation.file}:${violation.line} uses a JSX style prop`);
      console.error("  Move styling to utility classes or a styles.module.scss file.");
    }
    console.error("");
  }

  if (violations.length > 0) {
    console.error("Architecture boundary violations found:\n");
    for (const violation of violations) {
      console.error(`- src/${violation.file} imports "${violation.specifier}"`);
      console.error(`  ${violation.reason}`);
    }
  }
  process.exit(1);
}

console.log(`Architecture boundaries OK (${files.length} source files checked).`);
