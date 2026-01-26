# Ordinal CFA (WLSMV) using lavaan + semTools
# Rscript scripts/03_cfa_wlsmv.R
library(readr); library(lavaan); library(semTools)
dat <- read_csv("data/sem_df.csv", show_col_types=FALSE)
ordered_items <- colnames(dat)
model_ref <- '
SP =~ sp1 + sp2 + sp3 + sp4 + sp5 + sp6 + sp7 + sp8 + sp9 + sp10
CD =~ cd1 + cd2 + cd3 + cd4 + cd5
IR =~ ir1 + ir2 + ir3 + ir4 + ir5
sp4 ~~ sp5
cd1 ~~ cd2
cd2 ~~ cd3
ir3 ~~ ir4
ir4 ~~ ir5
'
fit_ref <- cfa(model_ref, data=dat, ordered=ordered_items, estimator="WLSMV")
write.csv(as.data.frame(t(fitMeasures(fit_ref, c("chisq","df","cfi","tli","rmsea","srmr")))),
          "outputs/cfa_fit_wlsmv_refined.csv", row.names=FALSE)
write.csv(round(as.matrix(htmt(fit_ref)),3), "outputs/HTMT_refined_polychoric.csv", row.names=TRUE)
