library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))

if(file.exists("DHT_dissemination_master_time.csv")){
    df <- read.table("DHT_dissemination_master_time.csv", header = TRUE, na.strings = "-1")
    p <- ggplot(df, aes(x=peer, y=dissemination_time, group=peer, colour=factor(peer), label=dissemination_time)) + theme_bw()
    p <- p + geom_point(alpha = 0.8)
    p <- p + geom_text(nudge_y = 0.8, size=3)
    p <- p + geom_vline(xintercept=df[is.na(df$dissemination_time) > 0,]$peer, colour="red", linetype = "dotted")
    # p <- p + facet_grid(operation ~ ., scales = "free_y")
    p <- p + theme(legend.position = "none")
    p <- p + labs(x = "\nPeer ID", y = "Dissemination time (milliseconds)\n")
        #p <- p + xlim(minX, maxX)
    ggsave(file="dht_dissemination_time.png", width=8, height=6, dpi=100)
}
