library(ggplot2)
library(reshape)
library(plyr)

if(file.exists("searches.txt")){
    df <- read.table("searches.txt", header = TRUE, check.names = FALSE)
    
    df <- ddply(df, "ttl", summarise, mduration = mean(duration), mcycles = mean(nrcycles), mmessages = mean(nrmessages), mumessages=mean(nruniquenodes))
    df <- melt(df, id="ttl")
    
    #remove duration for now
    df <- subset(df, variable != 'mduration')
    
    facetLabels <- list('mcycles'="Mean #cycles occurred", 'mduration'="Mean duration", 'mmessages'="Mean #messages sent", 'mumessages'="Mean #umessages sent")
    mf_labeller <- function(var, value){
        value <- as.character(value)
        return(facetLabels[value])
    }
    
    p <- ggplot(df, aes(ttl, value, fill=ttl, colour=ttl)) + theme_bw()
    p <- p + geom_bar(stat="identity")
    p <- p + facet_grid(variable ~ ., scales = "free_y", labeller=mf_labeller)
    p <- p + theme(legend.position="none")
    p <- p + labs(x = "\nTTL used in initial query", y = "Mean occurrences\n")
    p
    
    ggsave(file="search.png", width=8, height=6, dpi=100)
}