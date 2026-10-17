# Install the R package versions used to produce the committed outputs.
# Run from the repository root:  Rscript scripts/install_r_packages.R
repos <- getOption("repos")
if (is.null(repos) || identical(unname(repos["CRAN"]), "@CRAN@")) repos <- c(CRAN = "https://cloud.r-project.org")
pins <- c(lavaan = "0.6-17", semTools = "0.5-6")
for (pkg in names(pins)) {
  have <- tryCatch(as.character(packageVersion(pkg)), error = function(e) "")
  if (have == gsub("-", ".", pins[[pkg]])) next
  if (!requireNamespace("remotes", quietly = TRUE)) install.packages("remotes", repos = repos)
  remotes::install_version(pkg, version = pins[[pkg]], repos = repos, upgrade = "never")
}
cat("lavaan", as.character(packageVersion("lavaan")), "| semTools", as.character(packageVersion("semTools")), "\n")
