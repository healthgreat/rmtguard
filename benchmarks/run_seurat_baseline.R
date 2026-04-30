#!/usr/bin/env Rscript
# Author: RMTGuard development team
# Date: 2026-04-30
# Purpose: Run an optional Seurat v5-like baseline on prepared h5ad datasets.
# Data source: Public scRNA-seq h5ad files prepared by scripts/prepare_phase1_datasets.py.
# Method notes:
#   Seurat workflow: Hao et al., Cell 2021, DOI: 10.1016/j.cell.2021.04.048
#   h5ad import via zellkonverter/Bioconductor when available.

suppressPackageStartupMessages({
  required <- c("Seurat", "zellkonverter", "SingleCellExperiment", "SummarizedExperiment")
  missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0) {
    stop(
      "Missing required R packages for Seurat baseline: ",
      paste(missing, collapse = ", "),
      ". Install them before running this optional baseline.",
      call. = FALSE
    )
  }
})

parse_args <- function(args) {
  values <- list(
    input = NULL,
    dataset_id = NULL,
    label_key = NULL,
    outdir = file.path("results", "phase1_benchmarks"),
    npcs = c(30L, 50L),
    resolution = 1.0,
    random_state = 20260427L
  )
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (!startsWith(key, "--")) {
      stop("Unexpected positional argument: ", key, call. = FALSE)
    }
    name <- substring(key, 3L)
    if (name == "npcs") {
      i <- i + 1L
      pcs <- character()
      while (i <= length(args) && !startsWith(args[[i]], "--")) {
        pcs <- c(pcs, args[[i]])
        i <- i + 1L
      }
      values$npcs <- as.integer(pcs)
      next
    }
    if (i == length(args)) {
      stop("Missing value for argument: ", key, call. = FALSE)
    }
    value <- args[[i + 1L]]
    if (name %in% c("input", "dataset-id", "label-key", "outdir")) {
      values[[gsub("-", "_", name)]] <- value
    } else if (name %in% c("resolution")) {
      values[[name]] <- as.numeric(value)
    } else if (name %in% c("random-state")) {
      values[[gsub("-", "_", name)]] <- as.integer(value)
    } else {
      stop("Unknown argument: ", key, call. = FALSE)
    }
    i <- i + 2L
  }
  if (is.null(values$input) || is.null(values$dataset_id)) {
    stop("Required arguments: --input and --dataset-id", call. = FALSE)
  }
  values$npcs <- values$npcs[!is.na(values$npcs) & values$npcs > 0L]
  if (length(values$npcs) == 0L) {
    stop("--npcs must include at least one positive integer", call. = FALSE)
  }
  values
}

contains_non_ascii <- function(x) {
  codepoints <- utf8ToInt(enc2utf8(x))
  any(codepoints > 127L, na.rm = TRUE)
}

check_basilisk_cache_path <- function() {
  if (.Platform$OS.type != "windows") {
    return(invisible(TRUE))
  }
  if (nzchar(Sys.getenv("BASILISK_EXTERNAL_DIR"))) {
    return(invisible(TRUE))
  }
  home_path <- Sys.getenv("USERPROFILE", unset = path.expand("~"))
  if (contains_non_ascii(home_path)) {
    stop(
      "Windows user path contains non-ASCII characters and zellkonverter/basilisk may fail while creating its Python environment. ",
      "Set BASILISK_EXTERNAL_DIR to an ASCII-only directory before running this script, for example: ",
      "BASILISK_EXTERNAL_DIR=D:/BioSoft/basilisk-cache",
      call. = FALSE
    )
  }
  invisible(TRUE)
}

atomic_write_tsv <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  tmp <- paste0(path, ".tmp")
  utils::write.table(df, tmp, sep = "\t", quote = FALSE, row.names = FALSE)
  if (!file.rename(tmp, path)) {
    stop("Failed to atomically replace output file: ", path, call. = FALSE)
  }
}

normalized_mutual_information <- function(x, y) {
  tab <- table(x, y)
  if (sum(tab) == 0) {
    return(NA_real_)
  }
  pxy <- tab / sum(tab)
  px <- rowSums(pxy)
  py <- colSums(pxy)
  nz <- pxy > 0
  mi <- sum(pxy[nz] * log(pxy[nz] / (px[row(pxy)[nz]] * py[col(pxy)[nz]])))
  hx <- -sum(px[px > 0] * log(px[px > 0]))
  hy <- -sum(py[py > 0] * log(py[py > 0]))
  if ((hx + hy) == 0) {
    return(NA_real_)
  }
  2 * mi / (hx + hy)
}

adjusted_rand_index <- function(x, y) {
  if (!requireNamespace("mclust", quietly = TRUE)) {
    return(NA_real_)
  }
  mclust::adjustedRandIndex(as.factor(x), as.factor(y))
}

load_h5ad_as_seurat <- function(path) {
  check_basilisk_cache_path()
  sce <- zellkonverter::readH5AD(path)
  assay_names <- SummarizedExperiment::assayNames(sce)
  if (length(assay_names) == 0L) {
    stop("No assay found in h5ad input: ", path, call. = FALSE)
  }
  counts_assay <- if ("counts" %in% assay_names) "counts" else assay_names[[1L]]
  Seurat::as.Seurat(sce, counts = counts_assay, data = NULL)
}

run_seurat_baseline <- function(args) {
  set.seed(args$random_state)
  seu <- load_h5ad_as_seurat(args$input)
  max_npcs <- min(max(args$npcs), ncol(seu) - 1L, nrow(seu) - 1L)
  if (max_npcs < 1L) {
    stop("Input is too small for PCA baseline.", call. = FALSE)
  }
  seu <- Seurat::NormalizeData(seu, normalization.method = "LogNormalize", scale.factor = 10000, verbose = FALSE)
  seu <- Seurat::FindVariableFeatures(seu, selection.method = "vst", nfeatures = 2000, verbose = FALSE)
  seu <- Seurat::ScaleData(seu, features = rownames(seu), verbose = FALSE)
  seu <- Seurat::RunPCA(seu, npcs = max_npcs, verbose = FALSE)

  rows <- list()
  truth <- NULL
  if (!is.null(args$label_key) && args$label_key %in% colnames(seu[[]])) {
    truth <- as.character(seu[[args$label_key]][, 1L])
  }
  for (npc in args$npcs) {
    use_npc <- min(as.integer(npc), max_npcs)
    work <- Seurat::FindNeighbors(seu, dims = seq_len(use_npc), verbose = FALSE)
    work <- Seurat::FindClusters(
      work,
      resolution = args$resolution,
      algorithm = 1L,
      random.seed = args$random_state,
      verbose = FALSE
    )
    labels <- as.character(Seurat::Idents(work))
    rows[[length(rows) + 1L]] <- data.frame(
      dataset_id = args$dataset_id,
      method = paste0("seurat_v5_like_pcs_", npc),
      n_signal_pcs = use_npc,
      n_embedding_pcs = use_npc,
      baseline_pc_rule = paste0("seurat_v5_like_fixed_", npc),
      baseline_clusterer = "seurat_louvain",
      baseline_resolution = args$resolution,
      cluster_n = length(unique(labels)),
      ari = if (is.null(truth)) NA_real_ else adjusted_rand_index(truth, labels),
      nmi = if (is.null(truth)) NA_real_ else normalized_mutual_information(truth, labels),
      stringsAsFactors = FALSE
    )
  }
  do.call(rbind, rows)
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  outdir <- args$outdir
  dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
  logs_dir <- file.path(dirname(outdir), "..", "logs")
  dir.create(logs_dir, recursive = TRUE, showWarnings = FALSE)

  result <- run_seurat_baseline(args)
  out_path <- file.path(outdir, paste0(args$dataset_id, "_seurat_baseline.tsv"))
  atomic_write_tsv(result, out_path)
  capture.output(utils::sessionInfo(), file = file.path(logs_dir, "sessionInfo_seurat_baseline.txt"))
  message(out_path)
}

if (sys.nframe() == 0L) {
  main()
}
