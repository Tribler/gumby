library(ggplot2)
library(reshape)

if (file.exists("seeder.cc") && file.exists("leecher.cc")) {
    df_s <- read.table("seeder.cc", header = TRUE, check.names = FALSE,  fill = TRUE)
    df_l <- read.table("leecher.cc", header = TRUE, check.names = FALSE,  fill = TRUE)

    p <- ggplot(df_s, aes(x=time, y=hints_in)) + geom_line()
    p <- p + geom_line(data=df_l, aes(x=time, y=hints_out), colour="red")
    p <- p + theme(legend.position="top")
    p <- p + labs(x = "\nTime (Seconds)", y = "Outstanding requests\n")
    p

    ggsave(file="hints.png", width=8, height=6, dpi=100)
}

