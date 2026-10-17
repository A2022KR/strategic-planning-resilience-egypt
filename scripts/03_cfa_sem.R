# Ordinal CFA and latent mediation SEM (WLSMV) using lavaan + semTools
# Run from the repository root:  Rscript scripts/03_cfa_sem.R
options(warn = 1)
suppressPackageStartupMessages({library(lavaan); library(semTools)})
set.seed(20250520)

dat <- read.csv("data/sem_df.csv", check.names = FALSE)
items <- c(paste0("sp", 1:10), paste0("cd", 1:5), paste0("ir", 1:5))

# Categories 1-4 are very sparse (<2% of answers on every item); collapse them
# so that every threshold is estimable in every subsample: 1-4 / 5 / 6 / 7.
for (v in items) dat[[v]] <- pmax(dat[[v]], 4) - 3

samples <- list(
  "Full sample"                  = dat,
  "Screened 'Yes' only"          = dat[dat$screening == "yes", ],
  "Excluding straight-liners"    = dat[dat$straightline == 0, ],
  "Excluding repeat profiles"    = dat[dat$duplicate_profile == 0, ]
)

m1 <- 'G =~ sp1+sp2+sp3+sp4+sp5+sp6+sp7+sp8+sp9+sp10+cd1+cd2+cd3+cd4+cd5+ir1+ir2+ir3+ir4+ir5'
m2 <- 'SP =~ sp1+sp2+sp3+sp4+sp5+sp6+sp7+sp8+sp9+sp10
       CDIR =~ cd1+cd2+cd3+cd4+cd5+ir1+ir2+ir3+ir4+ir5'
m3 <- 'SP =~ sp1+sp2+sp3+sp4+sp5+sp6+sp7+sp8+sp9+sp10
       CD =~ cd1+cd2+cd3+cd4+cd5
       IR =~ ir1+ir2+ir3+ir4+ir5'
sem_model <- paste(m3, '
       CD ~ a*SP
       IR ~ b*CD + cp*SP
       ind := a*b
       total := cp + a*b
       prop := (a*b)/(cp + a*b)')

fitcols <- c("chisq.scaled", "df.scaled", "pvalue.scaled", "cfi.scaled", "tli.scaled",
             "rmsea.scaled", "rmsea.ci.lower.scaled", "rmsea.ci.upper.scaled", "srmr")

fit_rows <- list(); rel_rows <- list(); htmt_rows <- list(); load_rows <- list()
med_rows <- list(); phi_rows <- list(); diff_rows <- list()

for (s in names(samples)) {
  d <- samples[[s]]
  f1 <- cfa(m1, d, ordered = items, estimator = "WLSMV")
  f2 <- cfa(m2, d, ordered = items, estimator = "WLSMV")
  f3 <- cfa(m3, d, ordered = items, estimator = "WLSMV")
  for (nm in c("1-factor", "2-factor (SP; CD+IR)", "3-factor (SP; CD; IR)")) {
    f <- switch(nm, "1-factor" = f1, "2-factor (SP; CD+IR)" = f2, f3)
    fit_rows[[length(fit_rows) + 1]] <- data.frame(Sample = s, N = nobs(f), Model = nm,
                                                   as.list(round(unclass(fitMeasures(f, fitcols)), 3)), check.names = FALSE)
  }
  d32 <- lavTestLRT(f2, f3, method = "satorra.2000")
  d31 <- lavTestLRT(f1, f3, method = "satorra.2000")
  diff_rows[[s]] <- data.frame(Sample = s,
    Comparison = c("3-factor vs 2-factor", "3-factor vs 1-factor"),
    delta_chisq = round(c(d32[2, "Chisq diff"], d31[2, "Chisq diff"]), 2),
    delta_df = c(d32[2, "Df diff"], d31[2, "Df diff"]),
    p = signif(c(d32[2, "Pr(>Chisq)"], d31[2, "Pr(>Chisq)"]), 3))

  ss <- standardizedSolution(f3)
  ld <- ss[ss$op == "=~", c("lhs", "rhs", "est.std", "se")]
  load_rows[[s]] <- data.frame(Sample = s, Factor = ld$lhs, Item = ld$rhs,
                               Loading = round(ld$est.std, 3), SE = round(ld$se, 3))
  phi <- ss[ss$op == "~~" & ss$lhs != ss$rhs & ss$lhs %in% c("SP", "CD", "IR"), ]
  phi_rows[[s]] <- data.frame(Sample = s, Pair = paste(phi$lhs, phi$rhs, sep = "-"),
                              r = round(phi$est.std, 3),
                              ci_lower = round(phi$ci.lower, 3), ci_upper = round(phi$ci.upper, 3))

  cr <- compRelSEM(f3, ord.scale = TRUE)
  ave <- AVE(f3)
  rel_rows[[s]] <- data.frame(Sample = s, Construct = names(cr),
                              CompositeReliability = round(as.numeric(cr), 3),
                              AVE = round(as.numeric(ave[names(cr)]), 3))
  h <- htmt(m3, d, ordered = items)
  htmt_rows[[s]] <- data.frame(Sample = s, Pair = c("SP-CD", "SP-IR", "CD-IR"),
                               HTMT = round(c(h["CD", "SP"], h["IR", "SP"], h["IR", "CD"]), 3))

  fs <- sem(sem_model, d, ordered = items, estimator = "WLSMV")
  pe <- parameterEstimates(fs, standardized = TRUE)
  mc <- monteCarloCI(fs, nRep = 20000, standardized = TRUE)
  keep <- pe[pe$label %in% c("a", "b", "cp", "ind", "total", "prop"), ]
  keep <- keep[!duplicated(keep$label), ]
  med_rows[[s]] <- data.frame(Sample = s, N = nobs(fs), Path = keep$label,
                              Std_estimate = round(keep$std.all, 3),
                              p = signif(keep$pvalue, 3),
                              MC_CI_lower = round(mc[keep$label, "ci.lower"], 3),
                              MC_CI_upper = round(mc[keep$label, "ci.upper"], 3),
                              R2_CD = round(inspect(fs, "r2")["CD"], 3),
                              R2_IR = round(inspect(fs, "r2")["IR"], 3))
}

# Alternative specifications (full sample and excluding straight-liners):
#  - common latent method factor (equal loadings, orthogonal to traits)
#  - reverse order SP -> IR -> CD
#  - CD and IR merged into a single "preparedness capability" factor
all_items <- paste(items, collapse = " + ")
alt_models <- list(
  "Hypothesised (SP -> CD -> IR)" = sem_model,
  "Common method factor added" = paste(sem_model, '
       M =~ m*', gsub(" \\+ ", " + m*", all_items), '
       M ~~ 0*SP + 0*CD + 0*IR'),
  "Reverse order (SP -> IR -> CD)" = paste(m3, '
       IR ~ a*SP
       CD ~ b*IR + cp*SP
       ind := a*b
       total := cp + a*b
       prop := (a*b)/(cp + a*b)'),
  "Merged CD+IR (SP -> CDIR)" = paste(m2, '
       CDIR ~ a*SP')
)
alt_rows <- list()
for (s in c("Full sample", "Excluding straight-liners")) {
  d <- samples[[s]]
  for (nm in names(alt_models)) {
    fa <- sem(alt_models[[nm]], d, ordered = items, estimator = "WLSMV")
    if (!lavInspect(fa, "converged")) {
      message("Did not converge: ", nm, " / ", s)
      alt_rows[[length(alt_rows) + 1]] <- data.frame(Sample = s, Model = nm, chisq = NA, df = NA, cfi = NA,
        rmsea = NA, srmr = NA, a = NA, b = NA, c_prime = NA, p_c_prime = NA, indirect = NA,
        p_indirect = NA, mean_method_loading = NA, check.names = FALSE)
      next
    }
    pe <- parameterEstimates(fa, standardized = TRUE)
    get <- function(l) { v <- pe$std.all[pe$label == l]; if (length(v)) round(v[1], 3) else NA }
    getp <- function(l) { v <- pe$pvalue[pe$label == l]; if (length(v)) signif(v[1], 3) else NA }
    fm <- fitMeasures(fa, c("chisq.scaled", "df.scaled", "cfi.scaled", "rmsea.scaled", "srmr"))
    mload <- if (grepl("method", nm)) round(mean(pe$std.all[pe$lhs == "M" & pe$op == "=~"]), 3) else NA
    alt_rows[[length(alt_rows) + 1]] <- data.frame(
      Sample = s, Model = nm, chisq = round(fm[[1]], 1), df = fm[[2]], cfi = round(fm[[3]], 3),
      rmsea = round(fm[[4]], 3), srmr = round(fm[[5]], 3),
      a = get("a"), b = get("b"), c_prime = get("cp"), p_c_prime = getp("cp"),
      indirect = get("ind"), p_indirect = getp("ind"), mean_method_loading = mload, check.names = FALSE)
  }
}

out <- function(lst, file) write.csv(do.call(rbind, lst), file.path("outputs", file), row.names = FALSE)
out(alt_rows, "sem_alternative_models.csv")

# Power of the RMSEA test of close fit (MacCallum, Browne & Sugawara, 1996)
pw <- data.frame(Sample = names(samples), N = sapply(samples, nrow), df = 167,
                 power_close_vs_mediocre = sapply(samples, function(d)
                   round(findRMSEApower(rmsea0 = 0.05, rmseaA = 0.08, df = 167, n = nrow(d)), 3)))
write.csv(pw, file.path("outputs", "power_rmsea.csv"), row.names = FALSE)
out(fit_rows, "cfa_fit_wlsmv.csv")
out(diff_rows, "cfa_model_comparison.csv")
out(load_rows, "cfa_loadings.csv")
out(phi_rows, "latent_correlations.csv")
out(rel_rows, "reliability_cr_ave.csv")
out(htmt_rows, "htmt.csv")
out(med_rows, "sem_mediation_wlsmv.csv")
cat("Done. lavaan", as.character(packageVersion("lavaan")),
    "semTools", as.character(packageVersion("semTools")), "\n")
