library(ggplot2)
library(reshape)

if(file.exists("seeder.cc")){
    df <- read.table("seeder.err", header = TRUE, check.names = FALSE)

    p <- ggplot(df, aes(x=time, y=window))
    p <- p + theme(legend.position="top")
    p <- p + labs(x = "\nTime (Seconds)", y = "Window size\n", title = paste(output[1], "cc window"))
    p

    ggsave(file="seeder_window.png", width=8, height=6, dpi=100)
}

