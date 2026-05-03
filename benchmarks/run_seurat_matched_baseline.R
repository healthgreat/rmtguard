#!/usr/bin/env Rscript
# Author: RMTGuard development team
# Date: 2026-05-03
# Purpose: Run official Seurat v5 matched baseline pilots on prepared h5ad files.
# Data source: data/processed/*.h5ad.
# Method notes:
#   Seurat workflow follows the standard NormalizeData -> FindVariableFeatures
#   -> ScaleData -> RunPCA -> FindNeighbors -> FindClusters sequence.
#   Seurat reference: Hao et al., Cell 2021, DOI: 10.1016/j.cell.2021.04.048.
#   h5ad import uses zellkonverter/Bioconductor.

suppressPackageStartupMessages({
  required <- c(
    "Seurat",
    "zellkonverter",
    "SingleCellExperiment",
    "SummarizedExperiment",
    "Matrix",
    "mclust"
  )
  missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0) {
    stop(
      "Missing required R packages for Seurat matched baseline: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }
})

parse_args <- function(args) {
  values <- list(
    input = NULL,
    matrix_dir = NULL,
    dataset_id = NULL,
    label_key = "cell",
    batch_key = "batch",
    outdir = file.path("results", "submission"),
    run_label = "seurat_matched_subsample80_pilot10",
    n_repeats = 10L,
    subsample_fraction = 0.8,
    random_state = 20260427L,
    max_pcs = 50L,
    resolution = 1.0,
    methods = c("seurat_v5_fixed_30", "seurat_v5_fixed_50", "seurat_v5_elbow"),
    jackstraw_replicates = 20L
  )
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (!startsWith(key, "--")) {
      stop("Unexpected positional argument: ", key, call. = FALSE)
    }
    name <- substring(key, 3L)
    if (name == "methods") {
      i <- i + 1L
      methods <- character()
      while (i <= length(args) && !startsWith(args[[i]], "--")) {
        methods <- c(methods, args[[i]])
        i <- i + 1L
      }
      values$methods <- methods
      next
    }
    if (i == length(args)) {
      stop("Missing value for argument: ", key, call. = FALSE)
    }
    value <- args[[i + 1L]]
    field <- gsub("-", "_", name)
    if (field %in% c("input", "matrix_dir", "dataset_id", "label_key", "batch_key", "outdir", "run_label")) {
      values[[field]] <- value
    } else if (field %in% c("n_repeats", "random_state", "max_pcs", "jackstraw_replicates")) {
      values[[field]] <- as.integer(value)
    } else if (field %in% c("subsample_fraction", "resolution")) {
      values[[field]] <- as.numeric(value)
    } else {
      stop("Unknown argument: ", key, call. = FALSE)
    }
    i <- i + 2L
  }
  if (is.null(values$dataset_id) || (is.null(values$input) && is.null(values$matrix_dir))) {
    stop("Required arguments: --dataset-id and either --input or --matrix-dir", call. = FALSE)
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
      "Windows user path contains non-ASCII characters. Set BASILISK_EXTERNAL_DIR to an ASCII-only directory, for example D:/BioSoft/basilisk-cache.",
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

read_existing <- function(path) {
  if (!file.exists(path)) {
    return(data.frame())
  }
  utils::read.delim(path, stringsAsFactors = FALSE, check.names = FALSE)
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

metric_ari <- function(truth, pred) {
  truth <- as.factor(truth)
  pred <- as.factor(pred)
  if (length(unique(truth)) < 2L || length(unique(pred)) < 2L) {
    return(NA_real_)
  }
  mclust::adjustedRandIndex(truth, pred)
}

load_h5ad_as_seurat <- function(path) {
  check_basilisk_cache_path()
  sce <- zellkonverter::readH5AD(path)
  assay_names <- SummarizedExperiment::assayNames(sce)
  if (length(assay_names) == 0L) {
    stop("No assay found in h5ad input: ", path, call. = FALSE)
  }
  counts_assay <- if ("counts" %in% assay_names) "counts" else assay_names[[1L]]
  counts <- SummarizedExperiment::assay(sce, counts_assay)
  counts <- methods::as(counts, "dgCMatrix")
  storage.mode(counts@x) <- "double"
  metadata <- as.data.frame(SummarizedExperiment::colData(sce))
  Seurat::CreateSeuratObject(counts = counts, meta.data = metadata)
}

load_mtx_as_seurat <- function(matrix_dir) {
  matrix_path <- file.path(matrix_dir, "counts.mtx")
  features_path <- file.path(matrix_dir, "features.tsv")
  barcodes_path <- file.path(matrix_dir, "barcodes.tsv")
  obs_path <- file.path(matrix_dir, "obs.tsv")
  required <- c(matrix_path, features_path, barcodes_path, obs_path)
  missing <- required[!file.exists(required)]
  if (length(missing) > 0L) {
    stop("Missing MatrixMarket Seurat input file(s): ", paste(missing, collapse = ", "), call. = FALSE)
  }
  counts <- Matrix::readMM(matrix_path)
  counts <- methods::as(counts, "dgCMatrix")
  storage.mode(counts@x) <- "double"
  features <- make.unique(readLines(features_path, warn = FALSE))
  barcodes <- make.unique(readLines(barcodes_path, warn = FALSE))
  rownames(counts) <- features
  colnames(counts) <- barcodes
  metadata <- utils::read.delim(obs_path, stringsAsFactors = FALSE, check.names = FALSE)
  if ("cell_barcode" %in% colnames(metadata)) {
    rownames(metadata) <- make.unique(as.character(metadata$cell_barcode))
    metadata$cell_barcode <- NULL
  }
  metadata <- metadata[colnames(counts), , drop = FALSE]
  Seurat::CreateSeuratObject(counts = counts, meta.data = metadata)
}

split_indices <- function(dataset_id, n_cells, repeat_id, random_state, subsample_fraction) {
  dataset_seed <- sum(utf8ToInt(dataset_id))
  seed <- random_state + repeat_id * 997L + dataset_seed
  set.seed(seed)
  if (subsample_fraction < 1) {
    n_sub <- max(2L, as.integer(round(n_cells * subsample_fraction)))
    sort(sample.int(n_cells, n_sub, replace = FALSE))
  } else {
    seq_len(n_cells)
  }
}

choose_elbow_n_pcs <- function(variance_ratio, min_pcs = 5L) {
  n <- length(variance_ratio)
  if (n == 0L) {
    return(0L)
  }
  if (n <= min_pcs) {
    return(n)
  }
  cumulative <- cumsum(variance_ratio)
  x <- seq(0, 1, length.out = n)
  y <- (cumulative - cumulative[[1L]]) / max(cumulative[[n]] - cumulative[[1L]], .Machine$double.eps)
  distances <- y - x
  start <- max(1L, min_pcs)
  which.max(distances[start:n]) + start - 1L
}

run_one <- function(seu_all, args, repeat_id, method_id) {
  idx <- split_indices(
    args$dataset_id,
    ncol(seu_all),
    repeat_id,
    args$random_state,
    args$subsample_fraction
  )
  seu <- subset(seu_all, cells = colnames(seu_all)[idx])
  truth <- if (args$label_key %in% colnames(seu[[]])) {
    as.character(seu[[args$label_key]][, 1L])
  } else {
    rep(NA_character_, ncol(seu))
  }
  batch <- if (args$batch_key %in% colnames(seu[[]])) {
    as.character(seu[[args$batch_key]][, 1L])
  } else {
    rep(NA_character_, ncol(seu))
  }

  t0 <- proc.time()[["elapsed"]]
  seu <- Seurat::NormalizeData(seu, normalization.method = "LogNormalize", scale.factor = 10000, verbose = FALSE)
  seu <- Seurat::FindVariableFeatures(seu, selection.method = "vst", nfeatures = 2000, verbose = FALSE)
  seu <- Seurat::ScaleData(seu, features = rownames(seu), verbose = FALSE)
  max_npcs <- min(args$max_pcs, ncol(seu) - 1L, length(Seurat::VariableFeatures(seu)))
  if (max_npcs < 2L) {
    stop("Subset is too small for Seurat PCA.", call. = FALSE)
  }
  seu <- Seurat::RunPCA(seu, npcs = max_npcs, features = Seurat::VariableFeatures(seu), verbose = FALSE)
  method_label <- switch(
    method_id,
    seurat_v5_fixed_30 = "Seurat v5 fixed 30 PCs",
    seurat_v5_fixed_50 = "Seurat v5 fixed 50 PCs",
    seurat_v5_elbow = "Seurat v5 elbow-rule PCs",
    seurat_v5_jackstraw = "Seurat v5 JackStraw PCs",
    method_id
  )
  if (method_id == "seurat_v5_fixed_30") {
    selected_pcs <- min(30L, max_npcs)
    pc_rule <- "fixed_30"
  } else if (method_id == "seurat_v5_fixed_50") {
    selected_pcs <- min(50L, max_npcs)
    pc_rule <- "fixed_50"
  } else if (method_id == "seurat_v5_elbow") {
    stdev <- seu[["pca"]]@stdev
    variance_ratio <- stdev^2 / sum(stdev^2)
    selected_pcs <- min(max(1L, choose_elbow_n_pcs(variance_ratio, min_pcs = 5L)), max_npcs)
    pc_rule <- "elbow"
  } else if (method_id == "seurat_v5_jackstraw") {
    seu <- Seurat::JackStraw(seu, num.replicate = args$jackstraw_replicates, dims = max_npcs, verbose = FALSE)
    seu <- Seurat::ScoreJackStraw(seu, dims = seq_len(max_npcs))
    jack <- seu@reductions$pca@jackstraw$overall.p.values
    passing <- which(jack[, "Score"] <= 0.05)
    selected_pcs <- if (length(passing) == 0L) 1L else min(max(passing), max_npcs)
    pc_rule <- paste0("jackstraw_", args$jackstraw_replicates, "_replicates")
  } else {
    stop("Unknown method: ", method_id, call. = FALSE)
  }

  set.seed(args$random_state + repeat_id)
  seu <- Seurat::FindNeighbors(seu, dims = seq_len(selected_pcs), verbose = FALSE)
  seu <- Seurat::FindClusters(
    seu,
    resolution = args$resolution,
    algorithm = 1L,
    random.seed = args$random_state + repeat_id,
    verbose = FALSE
  )
  pred <- as.character(Seurat::Idents(seu))
  elapsed <- proc.time()[["elapsed"]] - t0
  row <- data.frame(
    run_label = args$run_label,
    dataset_id = args$dataset_id,
    method_id = method_id,
    method_label = method_label,
    method_family = "official Seurat baseline",
    repeat_id = repeat_id,
    execution_status = "official_seurat_complete",
    n_cells = length(pred),
    source_n_cells = ncol(seu_all),
    subsample_n_cells = length(pred),
    subsample_fraction = args$subsample_fraction,
    n_genes = nrow(seu),
    label_key = args$label_key,
    batch_key = args$batch_key,
    label_n = length(unique(truth)),
    batch_n = length(unique(batch)),
    analysis_status = "ok",
    no_call_reason = "",
    selected_pcs = selected_pcs,
    embedding_pcs = selected_pcs,
    pc_rule = pc_rule,
    cluster_n = length(unique(pred)),
    runtime_seconds = elapsed,
    peak_memory_mb = NA_real_,
    label_ari = metric_ari(truth, pred),
    label_nmi = normalized_mutual_information(truth, pred),
    batch_ari = metric_ari(batch, pred),
    batch_nmi = normalized_mutual_information(batch, pred),
    source_table = "computed_by_run_seurat_matched_baseline.R",
    method_notes = "Official Seurat v5 matched baseline on the same subsampling seed framework.",
    stringsAsFactors = FALSE
  )
  names(row)[names(row) == "repeat_id"] <- "repeat"
  row
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  if (!dir.exists(args$outdir)) {
    dir.create(args$outdir, recursive = TRUE, showWarnings = FALSE)
  }
  detail_path <- file.path(args$outdir, "seurat_matched_baseline_detail.tsv")
  existing <- read_existing(detail_path)
  rows <- list()
  if (nrow(existing) > 0L) {
    rows <- split(existing, seq_len(nrow(existing)))
  }
  completed <- if (nrow(existing) > 0L) {
    paste(existing$dataset_id, existing$method_id, existing[["repeat"]], existing$run_label, sep = "||")
  } else {
    character()
  }
  seu_all <- if (!is.null(args$matrix_dir)) {
    load_mtx_as_seurat(args$matrix_dir)
  } else {
    load_h5ad_as_seurat(args$input)
  }
  for (repeat_id in seq_len(args$n_repeats) - 1L) {
    for (method_id in args$methods) {
      key <- paste(args$dataset_id, method_id, repeat_id, args$run_label, sep = "||")
      if (key %in% completed) {
        next
      }
      row <- run_one(seu_all, args, repeat_id, method_id)
      rows[[length(rows) + 1L]] <- row
      atomic_write_tsv(do.call(rbind, rows), detail_path)
      completed <- c(completed, key)
    }
  }
  atomic_write_tsv(do.call(rbind, rows), detail_path)
  capture.output(utils::sessionInfo(), file = file.path(args$outdir, "sessionInfo_seurat_matched_baseline.txt"))
  message(detail_path)
}

if (sys.nframe() == 0L) {
  main()
}
